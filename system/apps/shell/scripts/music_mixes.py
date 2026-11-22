"""Local Daily Mix metadata snapshots; credentials never cross the bridge."""
from concurrent.futures import Future
import copy
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
import threading
import time
import uuid
from urllib.parse import urlparse

ORIGIN = 'https://xpui.app.spotify.com'


def playlist_uri(value):
    value = str(value or '').strip()
    if re.fullmatch(r'spotify:playlist:[A-Za-z0-9]{22}', value):
        return value
    url = urlparse(value)
    match = re.fullmatch(r'/(?:intl-[a-z]{2}/)?playlist/([A-Za-z0-9]{22})/?', url.path)
    if url.scheme == 'https' and url.netloc == 'open.spotify.com' and match:
        return 'spotify:playlist:' + match[1]
    raise ValueError('Paste a Spotify playlist link or spotify:playlist URI.')


def normalize(data):
    if not isinstance(data, dict) or not isinstance(data.get('mixes'), list) or len(data['mixes']) > 100:
        raise ValueError('Expected up to 100 Spotify playlists')
    mixes = []
    for mix in data['mixes']:
        if not re.fullmatch(r'spotify:playlist:[A-Za-z0-9]{22}', mix.get('uri', '')):
            raise ValueError('Invalid playlist')
        if not isinstance(mix.get('name'), str) or not 0 < len(mix['name'].strip()) <= 200:
            raise ValueError('Invalid playlist name')
        tracks = mix.get('tracks')
        if not isinstance(tracks, list) or not 0 < len(tracks) <= 10000:
            raise ValueError('Incomplete mix')
        cleaned = []
        for track in tracks:
            if not re.fullmatch(r'spotify:track:[A-Za-z0-9]{22}', track.get('uri', '')):
                raise ValueError('Invalid track')
            cleaned.append({key: str(track.get(key, ''))[:500] for key in ('uri', 'title', 'artist')})
        mixes.append(dict(uri=mix['uri'], name=mix['name'], tracks=cleaned))
    return mixes


class Mixes:  # pylint: disable=too-many-instance-attributes
    def __init__(self, path, read, write):
        self.path, self.write = path, write
        self.lock = threading.Lock()
        self.refresh_id = ''
        self.refresh_uri = ''
        self.preview = None
        self.suggestion = None
        self.suggestion_result = dict(tracks=[], pending=False, status='')
        self.playlist_write = None
        self.write_result = dict(pending=False, status='')
        self.refresh_started = 0
        self.refresh_status = ''
        self.data = read(path, dict(current=[], saved=[], checked=''))

    def play_suggestion(self, uri):
        if not isinstance(uri, str) or not re.fullmatch(r'spotify:track:[A-Za-z0-9]{22}', uri):
            raise ValueError('Choose a valid Spotify track to preview')
        from music_spotify import running
        if not running():
            raise ValueError('Open Spotify once, then play the suggestion again.')
        job = dict(id=uuid.uuid4().hex, uri=uri)
        result = Future()
        with self.lock:
            if self.preview:
                raise ValueError('Wait for the current Spotify preview to finish.')
            self.preview = (job, result)
        try:
            error = result.result(timeout=3)
            if error:
                raise ValueError(error)
            return dict(uri=uri, status='Playing through Spotify in the background')
        except TimeoutError:
            # Spotify may throttle its integration while the app is in the tray.
            pass
        finally:
            with self.lock:
                self.preview = None

        from music_preview import preview
        return preview(uri, start=False)

    def replace_playlist(self, uri, tracks):
        uri = playlist_uri(uri)
        if not isinstance(tracks, list) or len(tracks) > 10000 or any(
                not isinstance(t, str) or not re.fullmatch(r'spotify:track:[A-Za-z0-9]{22}', t) for t in tracks):
            raise ValueError('Every Music track needs a known Spotify identity before updating Spotify.')
        with self.lock:
            if self.playlist_write:
                raise ValueError('A Spotify playlist update is already pending.')
            self.playlist_write = dict(id=uuid.uuid4().hex, uri=uri, tracks=tracks,
                                       started=time.monotonic())
            self.write_result = dict(pending=True, status='Waiting for Spotify…')
            return copy.deepcopy(self.write_result)

    def playlist_write_status(self):
        with self.lock:
            if self.playlist_write and time.monotonic() - self.playlist_write['started'] > 120:
                self.playlist_write = None
                self.write_result = dict(pending=False, status='Spotify update could not be confirmed. Check the playlist in Spotify before retrying.')
            return copy.deepcopy(self.write_result)

    def suggest(self, playlist, uri):
        with self.lock:
            self.suggestion = dict(id=uuid.uuid4().hex, playlist=playlist, uri=uri, started=time.monotonic())
            self.suggestion_result = dict(playlist=playlist, sourceUri=uri, tracks=[], pending=True, hasMore=True, status='Waiting for Spotify…')
            return copy.deepcopy(self.suggestion_result)

    def more_suggestions(self, playlist):
        with self.lock:
            if self.suggestion_result.get('playlist') != playlist:
                raise ValueError('Suggestions changed; refresh and try again')
            if self.suggestion or not self.suggestion_result.get('hasMore', False):
                return copy.deepcopy(self.suggestion_result)
            self.suggestion = dict(id=uuid.uuid4().hex, playlist=playlist,
                uri=self.suggestion_result['sourceUri'],
                skip=[t['uri'].split(':')[-1] for t in self.suggestion_result['tracks']],
                started=time.monotonic())
            self.suggestion_result.update(pending=True, status='Loading more suggestions…')
            return copy.deepcopy(self.suggestion_result)

    def suggestions(self):
        with self.lock:
            if self.suggestion and time.monotonic() - self.suggestion['started'] > 45:
                self.suggestion = None
                self.suggestion_result.update(pending=False, hasMore=False, status='Spotify did not respond. Open Spotify with the updated integration, then refresh suggestions.')
            return copy.deepcopy(self.suggestion_result)

    def dispatch(self, cmd, args):
        with self.lock:
            if cmd in ('mixes_refresh', 'mixes_load'):
                uri = playlist_uri(args.get('link')) if cmd == 'mixes_load' else ''
                if self.refresh_id:
                    raise ValueError('Wait for the current Spotify request to finish.')
                self.refresh_uri = uri
                self.refresh_id = uuid.uuid4().hex
                self.refresh_started = time.monotonic()
                self.refresh_status = 'Waiting for Spotify…'
            if self.refresh_id and time.monotonic() - self.refresh_started > 90:
                self.refresh_status = 'Spotify did not respond. Open Spotify with the updated desktop integration and try again.'
                self.refresh_id = ''
            if cmd == 'mixes_save':
                mix = next((m for m in self.data['current'] if m['uri'] == args.get('uri')), None)
                if mix and args.get('version') != mix['version']:
                    raise ValueError('Mix changed; refresh before saving')
                if not mix:
                    raise ValueError('Mix no longer available; refresh and retry')
                if not any(m['version'] == mix['version'] and m['uri'] == mix['uri'] for m in self.data['saved']):
                    self.data['saved'].append(dict(copy.deepcopy(mix), savedAt=datetime.now(timezone.utc).isoformat()))
                    self.write(self.path, self.data)
            return dict(copy.deepcopy(self.data), refreshPending=bool(self.refresh_id), refreshStatus=self.refresh_status)

    def update(self, payload):  # pylint: disable=too-many-locals,too-many-branches
        if 'preview_id' in payload:
            with self.lock:
                if self.preview:
                    job, result = self.preview
                    if job['id'] == payload['preview_id'] and not result.done():
                        result.set_result(str(payload.get('error') or '')[:300])
            return
        if 'playlist_write_id' in payload:
            with self.lock:
                if self.playlist_write and payload['playlist_write_id'] == self.playlist_write['id']:
                    error = str(payload.get('error') or '')[:500]
                    self.write_result = dict(pending=False, status=error or 'Spotify playlist now matches Music.')
                    self.playlist_write = None
            return
        if 'suggestion_id' in payload:
            tracks = payload.get('tracks', [])
            if not isinstance(tracks, list) or len(tracks) > 100:
                raise ValueError('Invalid suggestions')
            # Reuse the strict metadata validation for Spotify tracks.
            cleaned = normalize(dict(mixes=[dict(uri='spotify:playlist:' + 'a'*22,
                name='Suggestions', tracks=tracks)]))[0]['tracks'] if tracks else []
            for track, source in zip(cleaned, tracks):
                art = source.get('art')
                image = re.fullmatch(r'(?:spotify:image:|https://i\.scdn\.co/image/)([a-fA-F0-9]{40})', art) if isinstance(art, str) else None
                if image:
                    track['art'] = 'https://i.scdn.co/image/' + image[1]
            with self.lock:
                if self.suggestion and payload['suggestion_id'] == self.suggestion['id']:
                    existing = self.suggestion_result['tracks']
                    seen = {t['uri'] for t in existing}
                    additions = []
                    for track in cleaned:
                        if track['uri'] not in seen:
                            additions.append(track)
                            seen.add(track['uri'])
                    error = str(payload.get('error') or '')
                    self.suggestion_result.update(tracks=existing + additions, pending=False,
                        hasMore=bool(additions) and not bool(error),
                        status=(error or ('Suggestions from Spotify' if additions else
                            'Spotify has no more new suggestions for this playlist.'))[:300])
                    self.suggestion = None
            return
        mixes = normalize(payload)
        now = datetime.now(timezone.utc).isoformat()
        with self.lock:
            for mix in mixes:
                mix['version'] = hashlib.sha256(json.dumps(mix['tracks'], sort_keys=True).encode()).hexdigest()
                mix['updated'] = now
                self.data['current'] = [m for m in self.data['current'] if m['uri'] != mix['uri']] + [mix]
            if mixes:
                self.data['checked'] = now
            if payload.get('refresh_id') and payload['refresh_id'] == self.refresh_id:
                self.refresh_id = ''
                self.refresh_status = (str(payload.get('error'))[:300] if payload.get('error') else
                    'Updated Spotify playlists.' if mixes else
                    'No mixes received. Open Made for You in Spotify, then try again.')
            self.write(self.path, self.data)

    def start(self):
        store = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def reply(self, code, data=None):
                body = json.dumps(data).encode() if data is not None else b''
                self.send_response(code)
                self.send_header('Access-Control-Allow-Origin', ORIGIN)
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.send_header('Access-Control-Allow-Private-Network', 'true')
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                if body: self.wfile.write(body)
            def allowed(self):
                return self.path == '/mixes' and self.headers.get('Origin') == ORIGIN
            def do_OPTIONS(self): self.reply(204 if self.allowed() else 403)
            def do_GET(self):
                if not self.allowed():
                    self.reply(403); return
                with store.lock:
                    self.reply(200, dict(preview=store.preview[0] if store.preview else None, refresh_id=store.refresh_id, playlist_uri=store.refresh_uri, playlist_write=({k: v for k, v in store.playlist_write.items() if k != "started"} if store.playlist_write else None), suggestion=({k: v for k, v in store.suggestion.items() if k != "started"} if store.suggestion else None)))
            def do_POST(self):
                if not self.allowed():
                    self.reply(403); return
                try:
                    size = int(self.headers.get('Content-Length', 0))
                    if not 0 < size <= 16 * 1024 * 1024: raise ValueError('Invalid size')
                    store.update(json.loads(self.rfile.read(size)))
                except (ValueError, TypeError, AttributeError, KeyError):
                    self.reply(400); return
                self.reply(204)
            def setup(self):
                super().setup()
                self.connection.settimeout(5)
        server = HTTPServer(('127.0.0.1', 19838), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server
