"""MovieBox adapter. Protocol adapted from MIT-licensed moviebox-tui.

See vendor/moviebox-tui/SOURCE.md and LICENSE-MIT for provenance.
Anonymous runtime credentials stay in memory and are never logged or persisted.
"""
import base64
from functools import lru_cache
import hashlib
import hmac
import json
import re
import threading
import time
from urllib.parse import parse_qsl, urlparse
from urllib.request import Request, urlopen
import uuid
from media_validation import InvalidMedia, remote_duration, validate_duration

HOSTS = ('https://api6.aoneroom.com', 'https://api5.aoneroom.com', 'https://api4.aoneroom.com')
# Public application signing material from the upstream adapter, not a user key.
SIGNING_MATERIAL = '76iRl07s0xSN9jqmEWAt79EBJZulIQIsV64FZr2O'
PREFIX = '/wefeed-mobile-bff/subject-api/'


class Client:
    def __init__(self):
        self.lock = threading.RLock()
        self.token = None
        self.host = 0
        self.info = json.dumps(dict(package_name='com.community.oneroom', version_name='3.0.03.0529.03', version_code=50020046,
            os='android', os_version='13', install_ch='ps', device_id=uuid.uuid4().hex, install_store='ps', gaid=str(uuid.uuid4()),
            brand='Redmi', model='23078RKD5C', system_language='en', net='NETWORK_WIFI', region='US', timezone='America/Phoenix', sp_code='40401'), separators=(',', ':'))

    def request(self, path, payload=None):
        with self.lock:
            if not self.token and path.startswith(PREFIX):
                self._request('/wefeed-mobile-bff/tab-operating?page=1&tabId=0&version=')
        return self._request(path, payload)

    def _request(self, path, payload=None):
        body = json.dumps(payload, separators=(',', ':')).encode() if payload is not None else None
        method = 'POST' if body is not None else 'GET'
        start_host = self.host
        for offset in range(len(HOSTS)):
            host_index = (start_host + offset) % len(HOSTS)
            url = HOSTS[host_index] + path
            timestamp = str(int(time.time() * 1000))
            parsed = urlparse(url)
            query = '&'.join(key + '=' + value for key, value in sorted(parse_qsl(parsed.query, keep_blank_values=True)))
            canonical = parsed.path + ('?' + query if query else '')
            message = '\n'.join([method, 'application/json', 'application/json', str(len(body)) if body is not None else '', timestamp,
                hashlib.md5(body[:102400]).hexdigest() if body is not None else '', canonical])
            key = base64.b64decode(SIGNING_MATERIAL + '==')
            signature = base64.b64encode(hmac.new(key, message.encode(), hashlib.md5).digest()).decode()
            headers = {'User-Agent': 'com.community.oneroom/50020046 (Linux; U; Android 13; en_US; 23078RKD5C; Build/TQ2A.230405.003; Cronet/135.0.7012.3)',
                'Accept': 'application/json', 'Content-Type': 'application/json', 'x-client-token': timestamp + ',' + hashlib.md5(timestamp[::-1].encode()).hexdigest(),
                'x-tr-signature': timestamp + '|2|' + signature, 'x-client-info': self.info, 'x-client-status': '0'}
            if self.token:
                headers['Authorization'] = 'Bearer ' + self.token
            try:
                with urlopen(Request(url, data=body, headers=headers), timeout=15) as response:
                    runtime_user = json.loads(response.headers.get('x-user', '{}'))
                    with self.lock:
                        self.token = runtime_user.get('token') or self.token
                    data = json.loads(response.read(8_000_000))
                if data.get('code') != 0:
                    continue
                self.host = host_index
                return data.get('data') or {}
            except (OSError, ValueError):
                continue
        raise RuntimeError('Movie/TV source is unavailable. Please retry later.')


CLIENT = Client()


def subject_id(show):
    identifier = show['id'].removeprefix('moviebox:')
    if not re.fullmatch(r'\d+', identifier):
        raise ValueError('Invalid movie/TV selection')
    return identifier


def subjects(value):
    """Extract cards from both homepage sections and grouped search results."""
    if isinstance(value, dict):
        if value.get('subjectId') and value.get('title') and value.get('subjectType'):
            yield value
        else:
            for child in value.values():
                yield from subjects(child)
    elif isinstance(value, list):
        for child in value:
            yield from subjects(child)


ENGLISH = {'en', 'eng', 'english', 'en-us', 'en-gb'}
FOREIGN_EDITION = re.compile(r'\b(hindi|tamil|telugu|malayalam|kannada|bengali|bangla|marathi|urdu|punjabi|arabic|korean|japanese|chinese|french|spanish|portuguese|ptbr|indonesian|thai|vietnamese|russian|german|turkish|persian|tagalog)\b', re.I)
CAM_MARKER = re.compile(r'\b(?:hd[ ._-]?cam|cam[ ._-]?rip|cam|hd[ ._-]?ts|telesync|telecine|ts|tc)\b', re.I)


def is_cam(item):
    if str(item.get('isCam', '')).lower() in ('true', '1', 'yes'):
        return True
    title = item.get('title') or ''
    labels = re.findall(r'\[([^]]+)\]|\(([^)]+)\)', title)
    if any(CAM_MARKER.search(' '.join(label)) for label in labels):
        return True
    # Match release tags, while allowing the actual movie title "Cam".
    if re.search(r'\s(?:HD[ ._-]?CAM|CAMRIP|CAM|HDTS|TELESYNC|TELECINE)(?:\s|$)', title, re.I):
        return True
    return any(CAM_MARKER.search(str(item.get(key) or '')) for key in ('quality', 'videoQuality', 'releaseType', 'corner'))


def english_label(value):
    words = [word.strip().lower() for word in re.split(r'[,;/+|]', str(value or ''))]
    return any(word in ENGLISH or re.fullmatch(r'en-[a-z]{2,4}|english (?:audio|dub(?:bed)?)', word) for word in words)


def foreign_edition(item):
    title = item.get('title') or ''
    labels = [' '.join(parts) for parts in re.findall(r'\[([^]]+)\]|\(([^)]+)\)', title)]
    return any(FOREIGN_EDITION.search(label) and not re.search(r'\b(?:english|eng)\b', label, re.I) for label in labels) or bool(re.search(FOREIGN_EDITION.pattern + r'\s+dub(?:bed)?\b', title, re.I))


def english_edition(item):
    """Verify this edition, not a different dub of the same production."""
    if is_cam(item) or foreign_edition(item):
        return False
    identifier = str(item.get('subjectId', ''))
    dubs = item.get('dubs') or []
    current = [dub for dub in dubs if isinstance(dub, dict) and str(dub.get('subjectId', '')) == identifier]
    if current:
        return any(english_label(dub.get('lanCode')) or english_label(dub.get('lanName')) for dub in current)
    if dubs:
        # English availability for another subject ID does not verify this one.
        return False
    audio = item.get('audioLanguage') or item.get('language')
    return english_label(audio)


@lru_cache(maxsize=512)
def _subject_info(identifier, time_bucket):
    return CLIENT.request(PREFIX + 'get?subjectId=' + identifier)


def subject_info(identifier):
    # Cache metadata for ten minutes, including across browsing/detail requests.
    return _subject_info(str(identifier), int(time.monotonic() // 600))


def viewing_edition(item):
    if is_cam(item) or foreign_edition(item):
        return None
    # Homepage cards omit edition language; fetch details before admitting them.
    item = dict(item, **subject_info(str(item['subjectId'])))
    return item if english_edition(item) else None


def cards(data, kind):
    found, seen = [], set()
    for item in subjects(data):
        if item.get('subjectType') != (1 if kind == 'movies' else 2) or not item.get('hasResource', True):
            continue
        # Mark every raw ID as seen, including rejected editions.
        identifier = 'moviebox:' + str(item['subjectId'])
        if identifier in seen:
            continue
        seen.add(identifier)
        item = viewing_edition(item)
        if item is None or not item.get('hasResource', True):
            continue
        title = re.sub(r'\s+S\d+(?:-S?\d+)?$', '', item['title'], flags=re.I)
        found.append(dict(id=identifier, kind=kind, title=title, image=(item.get('cover') or {}).get('url', ''),
            description=' · '.join(str(item[key]) for key in ('releaseDate', 'language', 'genre') if item.get(key)), url='', route='', viewingVerified=True))
    return found


def catalogue(kind, query, page):
    if query:
        data = CLIENT.request(PREFIX + 'search/v2', dict(keyword=query, page=page, perPage=20, subjectType='All', tabId='All'))
    else:
        data = CLIENT.request(f'/wefeed-mobile-bff/tab-operating?page={page}&tabId=0&version=')
    items = cards(data, kind)
    has_more = bool((data.get('pager') or {}).get('hasMore')) if query else bool(list(subjects(data))) and bool(items)
    return dict(items=items, hasMore=has_more)


def filter_history(shows):
    result = []
    for show in shows:
        item = subject_info(subject_id(show))
        if english_edition(item):
            result.append(dict(show, viewingVerified=True))
    return result


def seasons(show):
    data = CLIENT.request(PREFIX + 'season-info?subjectId=' + subject_id(show))
    return [dict(id=str(row['se']), title='Season ' + str(row['se']), maxEp=int(row.get('maxEp') or 0), allEp=row.get('allEp') or '')
        for row in data.get('seasons', []) if row.get('se') is not None]


def season_episodes(show, season_id):
    available = seasons(show)
    season = next((row for row in available if row['id'] == str(season_id)), None)
    if not season:
        raise ValueError('This season is unavailable')
    if season['allEp']:
        numbers = sorted(set(int(value) for value in re.findall(r'\d+', str(season['allEp']))))
    else:
        numbers = range(1, min(season['maxEp'], 2000) + 1)
    episodes = [str(season_id) + ':' + str(number) for number in numbers]
    return dict(episodes=episodes, episodeLabels={token: 'Episode ' + token.split(':')[1] for token in episodes}, seasonId=str(season_id), resumeIndex=0)


def details(show, saved=None):
    item = subject_info(subject_id(show))
    if not english_edition(item):
        raise ValueError('This edition is not verified English audio or is marked as a CAM release.')
    metadata = []
    for key, label in [('releaseDate', 'Released'), ('duration', 'Runtime'), ('genre', 'Genres'), ('language', 'Language'), ('countryName', 'Country'), ('imdbRatingValue', 'IMDb')]:
        if item.get(key):
            metadata.append(label + ': ' + str(item[key]))
    data = dict(description=item.get('description', ''), metadata=metadata, seasons=[], episodes=[], episodeLabels={}, warning='')
    if show['kind'] == 'movies':
        data.update(episodes=['movie'], episodeLabels={'movie': 'Movie'})
    else:
        data['seasons'] = seasons(show)
        if data['seasons']:
            preferred = str(saved or '').split(':')[0]
            season = next((row for row in data['seasons'] if row['id'] == preferred), data['seasons'][0])
            data.update(season_episodes(show, season['id']))
        else:
            data['warning'] = 'No seasons available from this source.'
    return data


def announcement_resource(item):
    url = str(item.get('resourceLink') or item.get('url') or '').lower()
    parsed = urlparse(url)
    if parsed.hostname == 'macdn.aoneroom.com' and parsed.path.startswith('/other/'):
        return True
    if any(marker in url for marker in ('80da52722ee7de7a4303290af6783424', 'b164fbfb4347792950bdfbfb563d39d9', '1c7de0bd3393702d9191801f15f88f8d', '9a0461bc39da389663bf3dbb17091d3f', '/notice.mp4')):
        return True
    try:
        size, duration = int(item.get('size') or 0), float(item.get('duration') or 0)
    except (ValueError, TypeError):
        return False
    return 0 < size < 2_000_000 and duration >= 300


def choose_resource(data, quality):
    resources = [item for item in data.get('list', []) if item.get('resourceLink', '').startswith('https://') and not item.get('requireMemberType') and not is_cam(item) and not announcement_resource(item)]
    if not resources:
        if any(announcement_resource(item) for item in data.get('list', [])):
            raise InvalidMedia('The movie/TV provider is returning announcement clips instead of full videos. Playback was blocked; this source is currently unavailable.')
        raise RuntimeError('No playable source is available for this selection.')
    resources.sort(key=lambda item: int(item.get('resolution') or 0), reverse=quality != 'worst')
    height = {'1080p': 1080, '720p': 720, '480p': 480}.get(quality)
    return next((item for item in resources if int(item.get('resolution') or 0) <= height), resources[0]) if height else resources[0]


def resolve(show_id, episode, quality):
    identifier = subject_id({'id': show_id})
    info = subject_info(identifier)
    if not english_edition(info):
        raise ValueError('This edition is not verified English audio or is marked as a CAM release.')
    route = PREFIX + f'resource?subjectId={identifier}&page=1&perPage=20'
    if episode != 'movie':
        if not re.fullmatch(r'\d+:\d+', episode):
            raise ValueError('Invalid TV episode')
        season, number = episode.split(':')
        route += f'&se={season}&ep={number}'
    data = CLIENT.request(route)
    chosen = choose_resource(data, quality)
    expected = float(chosen.get('duration') or data.get('durationSeconds') or (info.get('durationSeconds') if episode == 'movie' else 0) or 0)
    if not expected:
        raise InvalidMedia('The source did not provide a runtime to verify this video. Playback was blocked.')
    validate_duration(expected, remote_duration(chosen['resourceLink']))
    captions = chosen.get('extCaptions') or []
    subtitle = next((row.get('url') or row.get('captionUrl') or '' for row in captions if 'en' in str(row.get('language', '')).lower()), '')
    return [chosen['resourceLink'], '', subtitle if subtitle.startswith('https://') else '', '']
