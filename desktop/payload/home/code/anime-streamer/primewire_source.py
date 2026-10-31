"""Primewire metadata/source selection and user-assisted browser playback."""
from functools import lru_cache
import json
import re
import subprocess
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path
import browser_bridge
from media_validation import InvalidMedia, validate_duration

BASE = 'https://primewire.mov'


def get_json(url):
    if url.startswith(BASE + '/api/'):
        try:
            with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'}),timeout=20) as response:
                return json.loads(response.read(4_000_000))
        except HTTPError as error:
            if error.code in (400,404):
                return {'servers':[]} # An unlisted/unreleased title is not an outage.
            raise RuntimeError('Primewire could not list this title. Please retry later.') from None
    from app import fetch
    return json.loads(fetch(url))


def identifier(show):
    match = re.fullmatch(r'primewire:(movie|tv):(\d+)', show['id'])
    if not match:
        raise ValueError('Invalid Primewire title')
    return match[1], match[2]


@lru_cache(maxsize=512)
def _sources(media_type, tmdb, season, episode, bucket):
    params = dict(type=media_type, tmdb=tmdb)
    if media_type == 'tv':
        params.update(season=season, episode=episode)
    return get_json(BASE + '/api/v1/s?' + urlencode(params))


def sources(media_type, tmdb, season=1, episode=1):
    return _sources(media_type, str(tmdb), str(season), str(episode), int(time.monotonic() // 300))


def eligible(server):
    language = str(server.get('audio_language') or '').lower()
    if language not in ('en', 'eng', 'english') and not language.startswith('en-'):
        return False
    quality = str(server.get('quality') or '').upper()
    filename = str(server.get('file_name') or '')
    if quality in ('CAM', 'TS', 'TC', 'HDCAM', 'HDTS'):
        return False
    return not re.search(r'\b(?:HDCAM|HDTS|TELESYNC|TELECINE|CAMRIP)\b|[. _\[]CAM[. _\]]', filename, re.I)


def runtime(meta):
    value = str(meta.get('runtime') or '')
    hours = re.search(r'(\d+)\s*h', value, re.I)
    minutes = re.search(r'(\d+)\s*(?:min|m\b)', value, re.I)
    return (int(hours[1]) * 3600 if hours else 0) + (int(minutes[1]) * 60 if minutes else 0)


def lookup(kind, meta):
    media_type = 'movie' if kind == 'movies' else 'tv'
    tmdb = meta.get('moviedb_id') or meta.get('tmdb_id')
    if not tmdb:
        full = get_json(f'https://v3-cinemeta.strem.io/meta/{"movie" if kind == "movies" else "series"}/{meta["id"]}.json').get('meta') or {}
        tmdb = full.get('moviedb_id') or full.get('tmdb_id')
    if not tmdb or not str(tmdb).isdigit():
        return None
    data = sources(media_type, tmdb)
    if not any(eligible(server) for server in data.get('servers', [])):
        return None
    info = data.get('info') or {}
    if info.get('imdb_id') and info['imdb_id'] != meta['id']:
        return None
    # Metadata matching never substitutes for validating actual playback.
    return dict(id=f'primewire:{media_type}:{tmdb}', kind=kind, title=meta['name'], image=meta.get('poster') or info.get('tmdb_image') or '',
        description='English audio · ' + str(meta.get('releaseInfo') or meta.get('year') or ''), url='', route='',
        imdb=meta['id'], viewingVerified=True)


@lru_cache(maxsize=256)
def _metadata(imdb, kind, bucket):
    if not re.fullmatch(r'tt\d+', imdb):
        raise ValueError('Invalid catalogue title')
    data = get_json(f'https://v3-cinemeta.strem.io/meta/{"movie" if kind == "movies" else "series"}/{imdb}.json')
    return data.get('meta') or {}


def metadata(show):
    media_type, tmdb = identifier(show)
    imdb = show.get('imdb')
    if not imdb:
        imdb = (sources(media_type, tmdb).get('info') or {}).get('imdb_id')
    return _metadata(imdb or '', show['kind'], int(time.monotonic() // 3600))


def season_episodes(show, season_id):
    if not str(season_id).isdigit():
        raise ValueError('Invalid season')
    videos = metadata(show).get('videos') or []
    rows = [row for row in videos if str(row.get('season')) == str(season_id) and (row.get('episode') or row.get('number'))]
    rows.sort(key=lambda row: int(row.get('episode') or row['number']))
    episodes = [str(season_id) + ':' + str(row.get('episode') or row['number']) for row in rows]
    return dict(episodes=episodes, episodeLabels={token: 'Episode ' + token.split(':')[1] + ' · ' + (row.get('name') or '') for token, row in zip(episodes, rows)}, seasonId=str(season_id), resumeIndex=0)


def details(show, saved=None):
    meta = metadata(show)
    data = dict(description=meta.get('description') or '', metadata=[str(meta[key]) for key in ('releaseInfo','runtime','imdbRating') if meta.get(key)],
        seasons=[], episodes=[], episodeLabels={}, warning='Primewire opens a verification browser. Complete its check and start an English video; the verified stream then opens in mpv.')
    if show['kind'] == 'movies':
        data.update(episodes=['movie'], episodeLabels={'movie':'Movie'})
    else:
        numbers = sorted(set(int(row['season']) for row in meta.get('videos', []) if row.get('season') is not None))
        data['seasons'] = [dict(id=str(number), title='Season ' + str(number)) for number in numbers]
        if numbers:
            preferred = str(saved or '').split(':')[0]
            chosen = preferred if preferred in [str(n) for n in numbers] else str(numbers[0])
            data.update(season_episodes(show, chosen))
    return data


class PlaybackLinks(list):
    def __init__(self, url, audio_index):
        super().__init__([url, '', '', ''])
        self.audio_map = '0:' + str(audio_index)
        self.audio_language = 'eng,en'


def resolve(show_id, episode, quality):
    import stream_relay
    show = dict(id=show_id, kind='movies' if show_id.startswith('primewire:movie:') else 'tv')
    media_type, tmdb = identifier(show)
    params = dict(tmdb=tmdb)
    season, number = ('0','0') if episode == 'movie' else episode.split(':')
    if media_type == 'tv':
        if not season.isdigit() or not number.isdigit():
            raise ValueError('Invalid episode')
        params.update(season=season, episode=number)
    data = sources(media_type, tmdb, season, number)
    allowed = [server for server in data.get('servers', []) if eligible(server)]
    if not allowed:
        raise InvalidMedia('No English, non-CAM Primewire source is available for this selection.')
    meta = metadata(show)
    expected = runtime(meta)
    # Episode runtime may be absent; a full VOD playlist must still exceed 120s.
    page = BASE + '/embed/' + media_type + '?' + urlencode(params)
    selected = browser_bridge.resolve(page, expected)
    if selected.get('format') == 'hls':
        validate_duration(expected, float(selected.get('duration') or 0))
    height = {'1080p':1080,'720p':720,'480p':480,'worst':0}.get(quality)
    local = stream_relay.register(selected['url'], selected.get('headers') or {}, height)
    result = subprocess.run(['ffprobe','-v','error','-rw_timeout','15000000','-allowed_extensions','ALL','-allowed_segment_extensions','ALL','-extension_picky','0','-show_entries','format=duration:stream=index,codec_type:stream_tags=language','-of','json',local], capture_output=True,text=True,timeout=40)
    try:
        probe = json.loads(result.stdout)
        actual = float((probe.get('format') or {}).get('duration') or selected.get('duration') or 0)
    except (ValueError, TypeError):
        raise InvalidMedia('The selected source could not be verified. Try another Primewire source.') from None
    validate_duration(expected, actual)
    audio = [row for row in probe.get('streams', []) if row.get('codec_type') == 'audio']
    english = next((row for row in audio if str((row.get('tags') or {}).get('language', '')).lower() in ('en','eng','english')), None)
    if english is None and len(audio) == 1:
        english = audio[0] # Primewire explicitly labels this selected release English.
    if not any(row.get('codec_type') == 'video' for row in probe.get('streams', [])):
        raise InvalidMedia('The selected source did not contain a video track. Try another Primewire source.')
    if english is None or result.returncode:
        raise InvalidMedia('Could not identify a usable English audio track. Try another Primewire source.')
    try:
        decoded = subprocess.run(['ffmpeg','-v','error','-rw_timeout','15000000','-allowed_extensions','ALL','-allowed_segment_extensions','ALL','-extension_picky','0','-ss',str(min(600, actual / 2)),'-i',local,'-map','0:v:0','-frames:v','1','-an','-f','null','-'], capture_output=True,timeout=45)
    except subprocess.TimeoutExpired:
        raise InvalidMedia('The selected source could not play beyond its opening. Try another Primewire source.') from None
    if decoded.returncode:
        raise InvalidMedia('The selected source failed the mid-video playback check. Try another Primewire source.')
    return PlaybackLinks(local, english['index'])

@lru_cache(maxsize=256)
def _legacy_title(show_id, bucket):
    """Resolve old history IDs to the new source without deleting saved entries."""
    import moviebox_source
    import discovery_catalogue
    info = moviebox_source.subject_info(moviebox_source.subject_id({'id':show_id}))
    kind = 'movies' if info.get('subjectType') == 1 else 'tv'
    imdb = None
    if discovery_catalogue.CACHE.exists():
        import sqlite3
        with sqlite3.connect(discovery_catalogue.CACHE) as database:
            row = database.execute("SELECT key FROM cache WHERE key LIKE 'match-v1:%' AND json_extract(payload,'$.id')=? LIMIT 1",(show_id,)).fetchone()
        if row:
            imdb = row[0].rsplit(':',1)[-1]
    if imdb:
        meta = _metadata(imdb, kind, int(time.monotonic() // 3600))
    else:
        from urllib.parse import quote
        title = re.sub(r'\[[^]]*\]','',info.get('title','')).strip()
        data = get_json(f'https://v3-cinemeta.strem.io/catalog/{"movie" if kind == "movies" else "series"}/top/search={quote(title,safe="")}.json')
        meta = next((row for row in data.get('metas',[]) if discovery_catalogue.matches(row,info)),None)
    if not meta:
        raise InvalidMedia('This old history entry could not be matched to Primewire. Search for the title again.')
    if not meta.get('id'):
        meta = dict(meta,id=imdb)
    card = lookup(kind,meta)
    if card is None:
        raise InvalidMedia('No English, non-CAM Primewire source was found for this old history entry.')
    return card


def migrate_legacy(show_id):
    return _legacy_title(show_id,int(time.monotonic() // 600))


def filter_history(shows):
    result,seen=[],set()
    for show in shows:
        if show['id'].startswith('moviebox:'):
            show=migrate_legacy(show['id'])
        if show['id'] not in seen:
            result.append(show);seen.add(show['id'])
    return result
