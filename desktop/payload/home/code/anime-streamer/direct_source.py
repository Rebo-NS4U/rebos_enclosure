"""Stremio HTTP stream client. No torrent engine or browser fallback exists here."""
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import quote, urlparse

from media_validation import InvalidMedia, validate_duration
import primewire_source as metadata_source
import stream_relay

# Public, anonymous HTTP-only add-ons. Playback is independently checked below.
# Explicitly enable multi-language sources; the unconfigured endpoint can be empty.
ADDONS = (
    'https://87d6a6ef6b58-webstreamrmbg.baby-beamup.club/' + quote(json.dumps({'multi': 'on', 'includeExternalUrls': False, 'disableExtractor_moviebox': 'on'}, separators=(',', ':')), safe=''),
    'https://pengu.uk',
)
CONFIG = Path.home() / '.config/anime-streamer/http-addons.json'
CAM = re.compile(r'\b(?:cam|hdcam|camrip|hdts|telesync|telecine|ts|tc)\b', re.I)
ENGLISH = re.compile(r'\b(?:english|eng|en)\b|🇬🇧|🇺🇸', re.I)


def https_url(url):
    parsed = urlparse(str(url))
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise InvalidMedia('Only direct HTTPS video sources are allowed. Torrent and browser links are disabled.')
    return url


def get_json(url):
    https_url(url)
    try:
        response = subprocess.run(['curl', '-fLsS', '--proto', '=https', '--proto-redir', '=https', '--max-time', '25', '--max-filesize', '4000000', '-A', 'Mozilla/5.0', '-H', 'Accept: application/json', '--', url], capture_output=True, timeout=30)
        raw = response.stdout
        if response.returncode or len(raw) > 4_000_000:
            raise ValueError('unavailable response')
        return json.loads(raw)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise RuntimeError('The HTTPS stream source is unavailable. Please retry later.') from None


def addon_bases():
    try:
        manifests = json.loads(CONFIG.read_text())
    except FileNotFoundError:
        return ADDONS
    except (OSError, ValueError):
        raise RuntimeError('Could not read HTTPS source settings.') from None
    if not isinstance(manifests, list) or not 1 <= len(manifests) <= 4:
        raise RuntimeError('Configure between one and four HTTPS add-on manifest URLs.')
    return tuple(https_url(url).removesuffix('/manifest.json').rstrip('/') for url in manifests)


def identifier(show):
    match = re.fullmatch(r'direct:(movie|series):(tt\d+)', show['id'])
    if not match:
        raise ValueError('Invalid HTTPS media selection')
    return match[1], match[2]


def eligible(stream):
    if not isinstance(stream, dict) or any(stream.get(key) for key in ('infoHash', 'externalUrl', 'ytId', 'magnet', 'torrent')):
        return False
    try:
        https_url(stream.get('url', ''))
    except InvalidMedia:
        return False
    hints = stream.get('behaviorHints') or {}
    if hints.get('p2p') or stream.get('type') in ('torrent', 'p2p'):
        return False
    label = ' '.join(str(stream.get(key) or '') for key in ('name', 'title', 'description', 'language')) + ' ' + str(hints.get('filename') or '')
    return bool(ENGLISH.search(label)) and not CAM.search(label)


@lru_cache(maxsize=256)
def _streams(media_type, imdb, episode, bucket, bases):
    resource = imdb if media_type == 'movie' else imdb + ':' + episode
    rows, errors = [], []
    def load(base):
        return get_json(base + '/stream/' + media_type + '/' + quote(resource, safe=':') + '.json')
    with ThreadPoolExecutor(max_workers=len(bases)) as pool:
        futures = [pool.submit(load, base) for base in bases]
    for future in futures:
        try:
            data = future.result()
            if not isinstance(data.get('streams'), list):
                raise RuntimeError('Invalid HTTPS stream response')
            rows.extend(row for row in data['streams'] if eligible(row))
        except RuntimeError as error:
            errors.append(error)
    if errors and not rows:
        raise errors[0]
    return rows


def streams(media_type, imdb, episode='1:1'):
    return _streams(media_type, imdb, episode, int(time.monotonic() // 180), addon_bases())


def lookup(kind, meta):
    media_type = 'movie' if kind == 'movies' else 'series'
    if not re.fullmatch(r'tt\d+', meta['id']):
        return None
    if not streams(media_type, meta['id']):
        return None
    return dict(id=f'direct:{media_type}:{meta["id"]}', kind=kind, title=meta['name'],
                image=meta.get('poster') or '', description='English audio · HTTPS · ' + str(meta.get('releaseInfo') or ''),
                url='', route='', imdb=meta['id'], viewingVerified=True)


def metadata(show):
    media_type, imdb = identifier(show)
    return metadata_source._metadata(imdb, 'movies' if media_type == 'movie' else 'tv', int(time.monotonic() // 3600))


def season_episodes(show, season_id):
    if not str(season_id).isdigit():
        raise ValueError('Invalid season')
    rows = [row for row in metadata(show).get('videos', []) if str(row.get('season')) == str(season_id) and row.get('episode')]
    rows.sort(key=lambda row: int(row['episode']))
    episodes = [str(season_id) + ':' + str(row['episode']) for row in rows]
    return dict(episodes=episodes, episodeLabels={token: 'Episode ' + str(row['episode']) + ' · ' + (row.get('name') or '') for token, row in zip(episodes, rows)}, seasonId=str(season_id), resumeIndex=0)


def playback_selection(show, episodes, index, now=None):
    """Keep season browsing separate from the ordered series playback queue."""
    selected = episodes[index]
    season, number = map(int, selected.split(':'))
    now = now or datetime.now(timezone.utc)
    rows = {}
    videos = metadata(show).get('videos') or [dict(season=token.split(':')[0], episode=token.split(':')[1]) for token in episodes]
    for row in videos:
        try:
            key = (int(row['season']), int(row['episode']))
            if key[0] < 0 or key[1] <= 0 or (key[0] == 0) != (season == 0):
                continue  # Specials are a separate queue, never inserted into the story.
            released = row.get('released')
            if released:
                release_time = datetime.fromisoformat(released.replace('Z', '+00:00'))
                if release_time.tzinfo is None:
                    release_time = release_time.replace(tzinfo=timezone.utc)
                if release_time > now:
                    continue
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        rows.setdefault(key, row)
    # A manually chosen episode remains playable even with incomplete metadata.
    rows.setdefault((season, number), {})
    ordered = sorted(rows)
    queue = [f'{s}:{n}' for s, n in ordered]
    labels = dict(show.get('episodeLabels') or {})
    for (s, n), row in rows.items():
        if row.get('name') or f'{s}:{n}' not in labels:
            labels[f'{s}:{n}'] = f'Season {s} · Episode {n}' + (' · ' + row['name'] if row.get('name') else '')
    return dict(show, episodeLabels=labels), queue, queue.index(f'{season}:{number}')


def details(show, saved=None):
    meta = metadata(show)
    def names(value):
        if isinstance(value, str):
            return [value] if value.strip() else []
        if not isinstance(value, list):
            return []
        return list(dict.fromkeys(name.strip() for name in value if isinstance(name, str) and name.strip()))
    data = dict(description=meta.get('description') or '', metadata=[str(meta[key]) for key in ('releaseInfo', 'runtime', 'imdbRating') if meta.get(key)],
                title=meta.get('name') or show.get('title', ''),
                cast=names(meta.get('cast')), directors=names(meta.get('director')),
                genres=names(meta.get('genres')), year=str(meta.get('releaseInfo') or ''),
                runtime=str(meta.get('runtime') or ''), rating=str(meta.get('imdbRating') or ''),
                country=meta.get('country') or '', released=str(meta.get('released') or '')[:10],
                seasons=[], episodes=[], episodeLabels={}, warning='Direct HTTPS · No local torrents. Each stream is checked before playback.')
    if show['kind'] == 'movies':
        data.update(episodes=['movie'], episodeLabels={'movie': 'Movie'})
    else:
        numbers = sorted({int(row['season']) for row in meta.get('videos', []) if row.get('season') is not None})
        data['seasons'] = [dict(id=str(number), title='Season ' + str(number)) for number in numbers]
        if numbers:
            preferred = str(saved or '').split(':')[0]
            chosen = preferred if preferred in {str(number) for number in numbers} else str(numbers[0])
            data.update(season_episodes(show, chosen))
    return data


def migrate(show):
    if show['id'].startswith('direct:'):
        return show
    # Metadata migration only; never invoke the previous browser resolver.
    if re.fullmatch(r'tt\d+', str(show.get('imdb') or '')):
        meta = {'id': show['imdb']}
    elif show['id'].startswith('moviebox:'):
        import moviebox_source
        info = moviebox_source.subject_info(moviebox_source.subject_id(show))
        import discovery_catalogue
        title = info.get('title', '')
        kind = show['kind']
        payload = get_json('https://v3-cinemeta.strem.io/catalog/' + ('movie' if kind == 'movies' else 'series') + '/top/search=' + quote(title, safe='') + '.json')
        meta = next((row for row in payload.get('metas', []) if discovery_catalogue.matches(row, info)), None)
    else:
        meta = metadata_source.metadata(show)
    if not meta or not re.fullmatch(r'tt\d+', str(meta.get('id') or meta.get('imdb_id') or show.get('imdb') or '')):
        raise InvalidMedia('This old history entry could not be matched. Search for the title again.')
    imdb = meta.get('id') or meta.get('imdb_id') or show['imdb']
    return dict(show, id='direct:' + ('movie' if show['kind'] == 'movies' else 'series') + ':' + imdb, imdb=imdb, historyId=show.get('historyId') or show['id'])


def filter_history(shows):
    result, seen = [], set()
    for show in shows:
        upgraded = migrate(show)
        if upgraded['id'] not in seen:
            result.append(upgraded)
            seen.add(upgraded['id'])
    return result


def resolution(stream):
    match = re.search(r'\b(2160|1440|1080|720|576|480|360)p\b', str(stream.get('name', '')) + ' ' + str(stream.get('title', '')), re.I)
    return int(match[1]) if match else 0


def verify(stream, expected, quality):
    if not eligible(stream):
        raise InvalidMedia('No English, non-CAM HTTPS stream is available.')
    headers = (stream.get('behaviorHints') or {}).get('proxyHeaders', {}).get('request') or {}
    # Do not allow addon-controlled hop-by-hop or injected headers.
    headers = {key: value for key, value in headers.items() if key.lower() in ('referer', 'origin', 'user-agent', 'cookie', 'authorization') and isinstance(value, str) and '\r' not in value and '\n' not in value}
    height = {'1080p':1080, '720p':720, '480p':480, 'worst':0}.get(quality)
    local = stream_relay.register(https_url(stream['url']), headers, height)
    flags = ['-rw_timeout', '15000000', '-protocol_whitelist', 'http,https,tcp,tls,crypto,data']
    hls_flags = ['-allowed_extensions', 'ALL', '-allowed_segment_extensions', 'ALL', '-extension_picky', '0']
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', *flags, *hls_flags, '-show_entries', 'format=duration,format_name:stream=index,codec_type,height:stream_tags=language:chapter=start_time:chapter_tags=title', '-of', 'json', local], capture_output=True, text=True, timeout=35)
        probe = json.loads(result.stdout)
        duration = float((probe.get('format') or {}).get('duration') or 0)
        if result.returncode or not math.isfinite(duration) or duration < 120:
            raise InvalidMedia('The source did not contain a verified full video.')
        validate_duration(expected, duration)
        tracks = probe.get('streams') or []
        if not any(row.get('codec_type') == 'video' for row in tracks):
            raise InvalidMedia('The source has no video track.')
        video = next(row for row in tracks if row.get('codec_type') == 'video')
        if height and int(video.get('height') or 0) > height:
            raise InvalidMedia('The source exceeds the selected playback quality.')
        audio = [row for row in tracks if row.get('codec_type') == 'audio']
        english = next((row for row in audio if (row.get('tags') or {}).get('language', '').lower() in ('en', 'eng', 'english')), None)
        if english is None and len(audio) == 1 and not (audio[0].get('tags') or {}).get('language'):
            english = audio[0]  # Explicit English release label; no conflicting track tag.
        if english is None:
            raise InvalidMedia('The source has no verified English audio track.')
        is_hls = 'hls' in str((probe.get('format') or {}).get('format_name') or '').split(',')
        decoded = subprocess.run(['ffmpeg', '-v', 'error', *flags, *(hls_flags if is_hls else []), '-ss', str(min(600, duration / 2)), '-i', local, '-map', '0:v:0', '-frames:v', '1', '-an', '-f', 'null', '-'], capture_output=True, timeout=40)
        if decoded.returncode:
            raise InvalidMedia('The source failed its mid-video playback check.')
    except (subprocess.TimeoutExpired, ValueError, OSError):
        raise InvalidMedia('The HTTPS video could not be verified. Try again later.') from None
    links = metadata_source.PlaybackLinks(local, english['index'])
    links.is_hls = is_hls
    links.format_name = str((probe.get('format') or {}).get('format_name') or '')
    links.chapters = probe.get('chapters') or []
    return links


def resolve(show_id, episode, quality):
    import torbox_source
    show = dict(id=show_id, kind='movies' if episode == 'movie' else 'tv')
    if not show_id.startswith('direct:'):
        show = migrate(show)
    media_type, imdb = identifier(show)
    if media_type == 'series' and not re.fullmatch(r'\d+:\d+', episode):
        raise ValueError('Invalid episode')
    if torbox_source.read_key():
        expected = metadata_source.runtime(metadata(show))
        for stream in torbox_source.streams(media_type, imdb, episode, quality):
            try:
                return verify(stream, expected, quality)
            except InvalidMedia:
                continue
        raise InvalidMedia('No verified English, non-CAM video is cached on TorBox for this selection. No uncached download or local torrent was started.')
    rows = streams(media_type, imdb, episode)
    cap = {'1080p':1080, '720p':720, '480p':480}.get(quality)
    ranked = sorted(rows, key=resolution, reverse=quality != 'worst')
    if cap:
        ranked = [row for row in ranked if resolution(row) <= cap]
    expected = metadata_source.runtime(metadata(show))
    for stream in ranked[:3]:
        try:
            return verify(stream, expected, quality)
        except InvalidMedia:
            continue
    raise InvalidMedia('No working English, non-CAM HTTPS stream was found. Local torrents and browser fallback are disabled. Please retry later.')
