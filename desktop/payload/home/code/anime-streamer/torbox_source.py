"""Private TorBox device sign-in and cached-only HTTPS playback.

Only TorBox receives account credentials. Anonymous discovery returns metadata;
no torrent client is launched and no peer-to-peer connection is made locally.
"""
import json
from functools import lru_cache
import os
from pathlib import Path
import re
import tempfile
import threading
import time
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
import uuid

API = 'https://api.torbox.app/v1/api/'
# TorBox's published CDN domains (Help Center, 2026-10-27).
CDN_DOMAINS = ('torbox.app', 'tb-cdn.cx', 'tb-cdn.io', 'tb-cdn.pw', 'tb-cdn.sh', 'tb-cdn.st', 'tb-cdn.to', 'tb-cdn.earth')
CREDENTIAL = Path.home() / '.config/anime-streamer/torbox-key'
LOCK = threading.RLock()
_LINK_CANCEL = threading.Event()
_LINK_STATE = {'connected': False, 'text': 'TorBox is not connected.'}


class TorBoxError(RuntimeError):
    def __init__(self, code):
        self.code = code
        message = {
            'AUTH_ERROR': 'TorBox could not authorize this account. Check your account or activate the demo if available.',
            'API_ACCESS_DENIED': 'This TorBox account cannot use the API. Check your plan or activate the demo if available.',
            'DOWNLOAD_NOT_CACHED': 'This file is not cached on TorBox. No cloud download was started.',
            'RATE_LIMITED': 'TorBox is limiting requests. Please wait and retry.',
        }.get(code, 'TorBox could not complete this request. Check your connection and account, then retry.')
        super().__init__(message)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # Never forward an API key to a redirected host.


def request(path, key=None, query=None, body=None, form=None):
    if not re.fullmatch(r'[a-z/]+', path):
        raise ValueError('Invalid TorBox endpoint')
    url = API + path + ('?' + urlencode(query, doseq=True) if query else '')
    headers = {'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    payload = None
    if body is not None:
        payload = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    if form is not None:
        boundary = uuid.uuid4().hex
        payload = ''.join('--' + boundary + '\r\nContent-Disposition: form-data; name="' + field + '"\r\n\r\n' + str(value) + '\r\n' for field, value in form.items()).encode() + ('--' + boundary + '--\r\n').encode()
        headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
    try:
        try:
            response = build_opener(NoRedirect()).open(Request(url, data=payload, headers=headers), timeout=20)
        except HTTPError as error:
            if error.code == 429:
                raise TorBoxError('RATE_LIMITED') from None
            if error.code in (401, 403):
                raise TorBoxError('AUTH_ERROR') from None
            response = error
        with response:
            raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise ValueError('oversized response')
        data = json.loads(raw)
    except TorBoxError:
        raise
    except (OSError, ValueError):
        raise TorBoxError('UNAVAILABLE') from None
    if not isinstance(data, dict) or not data.get('success'):
        code = data.get('error', 'UNAVAILABLE') if isinstance(data, dict) else 'UNAVAILABLE'
        raise TorBoxError(str(code))
    return data.get('data')


def read_key():
    try:
        return CREDENTIAL.read_text().strip()
    except FileNotFoundError:
        return ''


def save_key(key):
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9._-]{16,512}', key):
        raise TorBoxError('AUTH_ERROR')
    CREDENTIAL.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.torbox-', dir=CREDENTIAL.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(key)
        os.replace(name, CREDENTIAL)
    finally:
        Path(name).unlink(missing_ok=True)


def status():
    with LOCK:
        saved = bool(read_key())
        data = dict(_LINK_STATE, connected=saved)
        if saved and not _LINK_STATE.get('connected'):
            data['text'] = 'TorBox connection saved. Check connection to verify your account.'
        return data


def connect_key(key):
    global _LINK_STATE
    result = account(key)
    with LOCK:
        _LINK_CANCEL.set()
        save_key(key)
        _LINK_STATE = result
    return result


def account(key=None):
    key = key or read_key()
    if not key:
        return {'connected': False, 'text': 'TorBox is not connected.'}
    data = request('user/me', key=key)
    plan = {0: 'Free', 1: 'Essential', 2: 'Pro', 3: 'Standard'}.get(data.get('plan'), 'Account')
    return {'connected': True, 'plan': plan, 'text': 'TorBox connected · ' + plan + ' · Cached HTTPS streams only.'}


def disconnect():
    global _LINK_CANCEL, _LINK_STATE
    with LOCK:
        _LINK_CANCEL.set()
        CREDENTIAL.unlink(missing_ok=True)
        _LINK_STATE = {'connected': False, 'text': 'TorBox disconnected from this player.'}
        return dict(_LINK_STATE)


def start_link(on_status):
    global _LINK_CANCEL, _LINK_STATE
    with LOCK:
        _LINK_CANCEL.set()
        cancel = _LINK_CANCEL = threading.Event()
    data = request('user/auth/device/start', query={'app': 'Media Browser'})
    url = data.get('verification_url_complete') or data.get('verification_url') or ''
    if urlparse(url).scheme != 'https' or urlparse(url).hostname not in ('torbox.app', 'www.torbox.app'):
        raise TorBoxError('AUTH_ERROR')
    device = data.get('device_code')
    if not isinstance(device, str) or not device:
        raise TorBoxError('AUTH_ERROR')
    interval = max(5, min(30, int(data.get('interval') or 5)))
    expiry = time.monotonic() + max(30, min(1800, int(data.get('expires_in') or 600)))
    public = {'connected': False, 'text': 'Approve Media Browser on TorBox to connect.', 'code': data.get('code') or data.get('user_code') or '', 'url': url}
    with LOCK:
        if cancel.is_set():
            return status()
        _LINK_STATE = public
    def poll():
        global _LINK_STATE
        delay = interval
        result = {'connected': False, 'text': 'TorBox sign-in expired. Press Connect to try again.'}
        while time.monotonic() < expiry and not cancel.wait(delay):
            try:
                token_data = request('user/auth/device/token', body={'device_code': device})
                key = token_data if isinstance(token_data, str) else (token_data.get('token') or token_data.get('api_key') or token_data.get('access_token'))
                result = account(key)
                with LOCK:
                    if cancel.is_set():
                        return
                    save_key(key)
                break
            except TorBoxError as error:
                if error.code in ('DEVICE_CODE_NOT_USED', 'AUTHORIZATION_PENDING'):
                    continue
                if error.code == 'SLOW_DOWN':
                    delay = min(30, delay + 5)
                    continue
                result = {'connected': False, 'text': str(error)}
                break
            except (ValueError, TypeError, AttributeError):
                result = {'connected': False, 'text': 'TorBox returned an invalid sign-in response. Please retry.'}
                break
        with LOCK:
            if cancel.is_set():
                return
            _LINK_STATE = result
            on_status(dict(result))
    threading.Thread(target=poll, daemon=True, name='torbox-sign-in').start()
    return public


def pick_file(files, media_type, episode):
    video = []
    for row in files or []:
        name = str(row.get('name') or row.get('short_name') or '')
        if not re.search(r'\.(?:mkv|mp4|m4v|webm|avi|mov)$', name, re.I) or re.search(r'\b(?:sample|trailer|preview)\b', name, re.I):
            continue
        if media_type == 'series':
            season, number = map(int, episode.split(':'))
            if not re.search(rf'(?i)(?<![A-Za-z0-9])(?:S0*{season}[ ._-]*E0*{number}(?!\d|E\d)|{season}x0*{number}(?!\d))', name):
                continue
        if row.get('id') is not None:
            video.append(row)
    return max(video, key=lambda row: int(row.get('size') or 0)) if video else None


def cdn_url(url, key):
    import direct_source
    direct_source.https_url(url)
    host = urlparse(url).hostname or ''
    if key in url and not any(host == domain or host.endswith('.' + domain) for domain in CDN_DOMAINS):
        raise TorBoxError('UNAVAILABLE')
    return url


def candidates_for(media_type, imdb, episode, quality='best'):
    import direct_source
    if media_type not in ('movie', 'series') or not re.fullmatch(r'tt\d+', imdb):
        raise ValueError('Invalid availability request')
    resource = imdb if media_type == 'movie' else imdb + ':' + episode
    # This request sends only an IMDb/episode ID, never TorBox credentials.
    data = direct_source.get_json('https://torrentio.strem.fun/stream/' + media_type + '/' + resource + '.json')
    candidates = []
    for row in data.get('streams', []):
        hash_ = str(row.get('infoHash') or '').lower()
        # The metadata hash is sent only to TorBox, never to a local torrent engine.
        label = dict(row, url='https://metadata.invalid/video')
        label.pop('infoHash', None)
        if re.fullmatch(r'[a-f0-9]{40}', hash_) and direct_source.eligible(label):
            candidates.append((hash_, row))
    cap = {'1080p':1080, '720p':720, '480p':480}.get(quality)
    candidates.sort(key=lambda value: direct_source.resolution(value[1]), reverse=quality != 'worst')
    if cap:
        candidates.sort(key=lambda value: direct_source.resolution(value[1]) > cap)
    return candidates[:60]


def cached_candidates(candidates, key):
    if not candidates:
        return {}
    cache = request('torrents/checkcached', key=key, query={'hash': [value[0] for value in candidates], 'format': 'object', 'list_files': 'true'})
    if isinstance(cache, list):
        cache = {row['hash']: row for row in cache if isinstance(row, dict) and row.get('hash')}
    return cache or {}


@lru_cache(maxsize=512)
def _availability(media_type, imdb, episode, key, bucket):
    candidates = candidates_for(media_type, imdb, episode)
    cache = cached_candidates(candidates, key)
    return any(pick_file((cache.get(hash_) or {}).get('files'), media_type, episode)
               for hash_, _ in candidates)


def availability(media_type, imdb, episode='1:1'):
    key = read_key()
    if not key:
        return 'unknown'
    try:
        found = _availability(media_type, imdb, episode, key, int(time.monotonic() // 300))
        if read_key() != key:
            return 'unknown'
        return 'cached' if found else 'uncached'
    except (RuntimeError, ValueError, TypeError, AttributeError):
        return 'unknown'


def streams(media_type, imdb, episode, quality='best'):
    key = read_key()
    if not key:
        return
    candidates = candidates_for(media_type, imdb, episode, quality)
    cache = cached_candidates(candidates, key)
    count = 0
    for hash_, row in candidates:
        cached = (cache or {}).get(hash_)
        if not cached or not pick_file(cached.get('files'), media_type, episode):
            continue
        # The server enforces this flag even if availability changed after lookup.
        if read_key() != key:
            return
        try:
            added = request('torrents/createtorrent', key=key, form={'magnet': 'magnet:?xt=urn:btih:' + hash_, 'seed': 3, 'allow_zip': 'false', 'add_only_if_cached': 'true'})
        except TorBoxError as error:
            if error.code == 'DOWNLOAD_NOT_CACHED':
                continue
            raise
        tid = added.get('torrent_id')
        if tid is None:
            raise TorBoxError('UNAVAILABLE')
        items = request('torrents/mylist', key=key, query={'id': tid, 'bypass_cache': 'true'})
        item = next((value for value in items if value.get('id') == tid), None) if isinstance(items, list) else items
        if not item or not item.get('download_finished'):
            continue
        file = pick_file(item.get('files'), media_type, episode)
        if file is None:
            continue
        url = request('torrents/requestdl', query={'token': key, 'torrent_id': tid, 'file_id': file['id'], 'redirect': 'false'})
        cdn_url(url, key)
        # TorBox CDN URLs may contain the account token. Only the private relay
        # receives them; ffprobe/mpv receive an opaque loopback URL instead.
        if read_key() != key:
            return
        yield {'url': url, 'name': 'TorBox HTTPS · English · ' + str(row.get('name') or ''), 'title': row.get('title') or '', 'behaviorHints': {'filename': file.get('name') or ''}}
        count += 1
        if count >= 3:
            break
