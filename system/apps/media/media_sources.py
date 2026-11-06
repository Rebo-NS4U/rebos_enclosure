"""Movie/TV catalogue adapter and YouTube extraction, independent of the UI."""
from dataclasses import dataclass
import youtube_account
import time
import moviebox_source
import primewire_source
import discovery_catalogue
import direct_source
import json
from concurrent.futures import ThreadPoolExecutor
import torbox_source
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlparse, parse_qs

KINDS = ('anime', 'movies', 'tv', 'youtube')
YOUTUBE_RECOMMENDATIONS = (
    dict(id='for-you', title='For You', query=''),
    dict(id='most-popular', title='Popular', query='popular videos'),
    dict(id='youtube-music', title='Music', query='music official live performances'),
    dict(id='youtube-gaming', title='Gaming', query='gaming gameplay highlights'),
    dict(id='youtube-tech', title='Tech', query='technology reviews gadgets'),
    dict(id='youtube-learning', title='Learning', query='science history educational explainers'),
    dict(id='youtube-movies', title='Movies & TV', query='movies television trailers interviews'),
    dict(id='youtube-news', title='News', query='latest world news reports'),
    dict(id='youtube-live', title='Live', query='live streams news nature cameras'),
)
AVAILABILITY = ThreadPoolExecutor(max_workers=4, thread_name_prefix='availability')


def kind_of(show):
    kind = show.get('kind', 'anime')
    if kind not in KINDS:
        raise ValueError('Unsupported media type')
    return kind


@dataclass(frozen=True)
class CatalogueOptions:
    fetch: object = None
    check_availability: bool = True


def catalogue(kind, category, query, page, **controls):
    options = CatalogueOptions(**controls)
    if kind == 'youtube':
        if category == 'for-you' and not query.strip():
            return youtube_for_you(page)
        topic = next((row for row in YOUTUBE_RECOMMENDATIONS if row['id'] == category), YOUTUBE_RECOMMENDATIONS[0])
        items = youtube_catalogue(query.strip() or topic['query'], page)
        collection = '/@' in query or '/channel/' in query
        has_more = bool(items) and page < 10 and (not query.startswith(('https://', 'http://')) or (collection and 'list=' not in query))
        return dict(items=items, hasMore=has_more)
    if options.fetch is None:
        raise ValueError('Discovery requires an HTTPS fetcher')
    result = discovery_catalogue.catalogue(kind, category, page, options.fetch, query)
    return dict(result, items=availability_labels(result['items'])) if options.check_availability else result


def refresh_availability(items, done):
    """Publish each read-only label separately without holding up catalogue work."""
    def finished(future):
        try:
            labels = future.result()
        except Exception:
            return  # Keep the honest unknown label if a check fails.
        done(labels)
    for show in items:
        AVAILABILITY.submit(availability_labels, [show]).add_done_callback(finished)


def availability_labels(items):
    """Read-only cache checks: never add files or generate signed download links."""
    def label(show):
        show = dict(show)
        if show.get('kind') not in ('movies', 'tv'):
            return show
        media_type = 'movie' if show['kind'] == 'movies' else 'series'
        imdb = show.get('imdb') or show['id'].split(':')[-1]
        state = torbox_source.availability(media_type, imdb)
        text = {'cached': 'Cached on TorBox', 'uncached': 'No cached source found',
                'unknown': 'Availability not confirmed'}[state]
        if media_type == 'series':
            text += ' · S1 E1'
        return dict(show, sourceAvailability=state, availabilityLabel=text)
    if len(items) <= 1:
        return [label(show) for show in items]
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix='availability-batch') as pool:
        return list(pool.map(label, items))


def details(show, fetch=None, saved=None):
    if kind_of(show) == 'youtube':
        return youtube_details(show)
    upgraded = direct_source.migrate(show)
    data = direct_source.details(upgraded, saved)
    data['show'] = upgraded
    return data


def season_episodes(show, season_id):
    return direct_source.season_episodes(direct_source.migrate(show), season_id)


def playback_selection(show, episodes, index):
    if kind_of(show) == 'tv':
        selected, queue, position = direct_source.playback_selection(direct_source.migrate(show), episodes, index)
        return dict(show, episodeLabels=selected['episodeLabels']), queue, position
    return show, episodes, index


def resolve_movie(show_id, episode, quality):
    return direct_source.resolve(show_id, episode, quality)


def youtube_url(value):
    parsed = urlparse(value)
    if parsed.scheme != 'https' or parsed.hostname not in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be') or parsed.username or parsed.password:
        raise ValueError('Paste an HTTPS YouTube video, channel or playlist link')
    return value


def ytdlp(args, timeout=100, browser=None):
    executable = shutil.which('yt-dlp') or str(Path.home() / '.local/bin/yt-dlp')
    account = youtube_account.selection() if browser is None else browser
    auth = ['--cookies-from-browser', account] if account else []
    try:
        result = subprocess.run([executable, *auth, '--ignore-config', '--no-warnings', '--socket-timeout', '15', '--retries', '1', '--extractor-retries', '1', '--js-runtimes', 'node', *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError('YouTube took too long to respond. Try again.') from None
    if result.returncode:
        # Do not expose signed stream links/cookies in errors.
        message = 'YouTube could not load this item. It may require sign-in, be unavailable, or need an updated yt-dlp.'
        raise RuntimeError(message)
    return result.stdout


def fetch_youtube_feed(browser):
    payload = json.loads(ytdlp(['--flat-playlist', '--dump-single-json', '--skip-download',
                               '--playlist-end', '200', '--', ':ytrec'], browser=browser))
    entries = [youtube_card(row) for row in payload.get('entries', []) if row and row.get('id')]
    entries = list({row['id']: row for row in entries}.values())
    if not entries:
        raise ValueError('YouTube returned no recommendations. Check your browser sign-in and YouTube watch history.')
    return entries


def youtube_for_you(page):
    browser = youtube_account.selection()
    if not browser:
        raise ValueError('Connect your YouTube account above to load For You, or choose a public topic.')
    with youtube_account.LOCK:
        cached = youtube_account.FEEDS.get(browser)
    if page == 1 or cached is None or time.monotonic() - cached[0] > 600:
        youtube_account.assert_signed_in(browser)
        items = fetch_youtube_feed(browser)
        with youtube_account.LOCK:
            youtube_account.FEEDS[browser] = (time.monotonic(), items)
    else:
        items = cached[1]
    start = (page - 1) * 20
    return dict(items=items[start:start + 20], hasMore=start + 20 < len(items))


def youtube_queue(show, episodes, index, cards):
    """Single videos continue through the visible feed; playlists keep their order."""
    if kind_of(show) != 'youtube' or len(episodes) != 1 or not cards:
        return show, episodes, index
    queue, labels = [], {}
    for row in cards[:200]:
        url = youtube_url(row.get('url', ''))
        parsed = urlparse(url)
        if not (parse_qs(parsed.query).get('v') or parsed.hostname == 'youtu.be'):
            continue
        if url not in labels:
            queue.append(url)
            labels[url] = str(row.get('title', 'Video'))
    if episodes[0] not in queue:
        return show, episodes, index
    return dict(show, episodeLabels=labels), queue, queue.index(episodes[0])


def youtube_card(entry):
    identifier = str(entry['id'])
    if not re.fullmatch(r'[\w-]+', identifier):
        raise ValueError('Invalid YouTube item')
    is_playlist = entry.get('_type') in ('playlist', 'url_transparent') and (identifier.startswith(('PL', 'UU', 'RD')) or 'list=' in entry.get('url', ''))
    url = entry.get('webpage_url') or entry.get('url') or ''
    if not url.startswith('https://'):
        url = ('https://www.youtube.com/playlist?list=' if is_playlist else 'https://www.youtube.com/watch?v=') + identifier
    youtube_url(url)
    thumbnails = entry.get('thumbnails') or []
    image = entry.get('thumbnail') or (thumbnails[-1].get('url', '') if thumbnails else '')
    if not is_playlist and len(identifier) == 11:
        # Search thumbnails can negotiate AVIF despite a .jpg suffix; use the
        # stable JPEG endpoint that Qt can decode without a conversion request.
        image = 'https://i.ytimg.com/vi/' + identifier + '/hqdefault.jpg'
    duration = entry.get('duration')
    summary = entry.get('channel') or entry.get('uploader') or ''
    if duration:
        summary += f' · {int(duration) // 60}:{int(duration) % 60:02}'
    return dict(id='youtube:' + identifier, kind='youtube', title=entry.get('title') or identifier, image=image, description=summary, url=url)


def youtube_catalogue(query, page):
    query = query.strip() or 'popular videos'
    start, end = (page - 1) * 20 + 1, page * 20
    if page > 10:
        return []
    if query.startswith(('https://', 'http://')):
        url = youtube_url(query)
        if 'list=' in url:
            if page > 1:
                return []
            payload = json.loads(ytdlp(['--flat-playlist', '--dump-single-json', '--skip-download', '--yes-playlist', '--playlist-end', '1', '--', url]))
            # A watch URL with a list still opens the whole playlist.
            payload['webpage_url'] = 'https://www.youtube.com/playlist?list=' + parse_qs(urlparse(url).query)['list'][0]
            payload['_type'] = 'playlist'
            return [youtube_card(payload)]
        if 'list=' not in url and '/@' not in url and '/channel/' not in url and '/playlist' not in url:
            if page > 1:
                return []
            payload = json.loads(ytdlp(['--dump-single-json', '--skip-download', '--no-playlist', '--', url]))
            return [youtube_card(payload)]
        target = url
    else:
        target = f'ytsearch{end}:' + query
    output = ytdlp(['--flat-playlist', '--dump-json', '--skip-download', '--playlist-start', str(start), '--playlist-end', str(end), '--', target])
    return [youtube_card(json.loads(line)) for line in output.splitlines() if line.strip()]


def youtube_details(show):
    url = youtube_url(show['url'])
    is_playlist = 'list=' in url and not parse_qs(urlparse(url).query).get('v')
    args = ['--dump-single-json', '--skip-download']
    args += ['--flat-playlist', '--playlist-end', '100'] if is_playlist else ['--no-playlist']
    payload = json.loads(ytdlp(args + ['--', url]))
    entries = payload.get('entries', []) if is_playlist else [payload]
    entries = [entry for entry in entries if entry and entry.get('id') and entry.get('availability') not in ('private', 'premium_only', 'subscriber_only')]
    episodes, labels = [], {}
    for entry in entries:
        token = youtube_card(entry)['url']
        episodes.append(token)
        labels[token] = entry.get('title', 'Video')
    return dict(description=payload.get('description') or show.get('description', ''), metadata=[value for value in [payload.get('channel'), payload.get('upload_date')] if value], episodes=episodes, episodeLabels=labels, seasons=[], warning='Playlists show up to 100 videos.' if is_playlist else '')


def youtube_format(quality):
    height = {'1080p': 1080, '720p': 720, '480p': 480}.get(quality)
    fmt = f'bv*[height<={height}]+ba/b[height<={height}]' if height else ('worst' if quality == 'worst' else 'bv*+ba/b')
    # Prefer verified direct streams: an accessible HLS manifest can still point
    # to segments that YouTube rejects with 403 after the player opens it.
    limit = f'[height<={height}]' if height else ''
    direct = f'bv*{limit}[protocol=https]+ba[protocol=https]/b{limit}[protocol=https]'
    if quality == 'worst':
        direct = 'worst[protocol=https]'
    return direct + "/" + fmt


def resolve_youtube(episode, quality):
    youtube_url(episode)
    payload = json.loads(ytdlp(['--no-playlist', '--check-formats', '--dump-single-json', '--skip-download', '-S', 'res,fps,vcodec:h264,acodec:aac', '-f', youtube_format(quality), '--', episode]))
    streams = payload.get('requested_formats') or []
    if streams:
        video = next((stream for stream in streams if stream.get('vcodec') != 'none'), streams[0])
        audio = next((stream['url'] for stream in streams if stream.get('vcodec') == 'none'), '')
        link = video['url']
    else:
        link, audio = payload.get('url', ''), ''
    if not link.startswith('https://'):
        raise RuntimeError('YouTube returned no playable stream')
    native = payload.get('subtitles') or {}
    automatic = payload.get('automatic_captions') or {}
    english = native.get('en') or next((value for key, value in native.items() if key.startswith('en-')), [])
    if not english:
        english = automatic.get('en') or next((value for key, value in automatic.items() if key.startswith('en-')), [])
    subtitle = next((track['url'] for track in english if track.get('ext') == 'vtt'), '')
    return [link, 'https://www.youtube.com/', subtitle, audio]
