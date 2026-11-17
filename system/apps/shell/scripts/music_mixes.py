"""Local Daily Mix metadata snapshots; credentials never cross the bridge."""
import copy
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
import threading

ORIGIN = 'https://xpui.app.spotify.com'


def normalize(data):
    if not isinstance(data, dict) or not isinstance(data.get('mixes'), list) or len(data['mixes']) > 6:
        raise ValueError('Expected up to six Daily Mixes')
    mixes = []
    for mix in data['mixes']:
        if not re.fullmatch(r'spotify:playlist:[A-Za-z0-9]{22}', mix.get('uri', '')):
            raise ValueError('Invalid playlist')
        if not re.fullmatch(r'Daily Mix [1-6]', mix.get('name', '')):
            raise ValueError('Invalid Daily Mix name')
        tracks = mix.get('tracks')
        if not isinstance(tracks, list) or not 0 < len(tracks) <= 1000:
            raise ValueError('Incomplete mix')
        cleaned = []
        for track in tracks:
            if not re.fullmatch(r'spotify:track:[A-Za-z0-9]{22}', track.get('uri', '')):
                raise ValueError('Invalid track')
            cleaned.append({key: str(track.get(key, ''))[:500] for key in ('uri', 'title', 'artist')})
        mixes.append(dict(uri=mix['uri'], name=mix['name'], tracks=cleaned))
    return mixes


class Mixes:
    def __init__(self, path, read, write):
        self.path, self.write = path, write
        self.lock = threading.Lock()
        self.data = read(path, dict(current=[], saved=[], checked=''))

    def dispatch(self, cmd, args):
        with self.lock:
            if cmd == 'mixes_save':
                mix = next((m for m in self.data['current'] if m['uri'] == args.get('uri')), None)
                if mix and args.get('version') != mix['version']:
                    raise ValueError('Mix changed; refresh before saving')
                if not mix:
                    raise ValueError('Mix no longer available; refresh and retry')
                if not any(m['version'] == mix['version'] and m['uri'] == mix['uri'] for m in self.data['saved']):
                    self.data['saved'].append(dict(copy.deepcopy(mix), savedAt=datetime.now(timezone.utc).isoformat()))
                    self.write(self.path, self.data)
            return copy.deepcopy(self.data)

    def update(self, payload):
        mixes = normalize(payload)
        now = datetime.now(timezone.utc).isoformat()
        with self.lock:
            for mix in mixes:
                mix['version'] = hashlib.sha256(json.dumps(mix['tracks'], sort_keys=True).encode()).hexdigest()
                mix['updated'] = now
                self.data['current'] = [m for m in self.data['current'] if m['uri'] != mix['uri']] + [mix]
            self.data['checked'] = now
            self.write(self.path, self.data)

    def start(self):
        store = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def reply(self, code):
                self.send_response(code)
                self.send_header('Access-Control-Allow-Origin', ORIGIN)
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.send_header('Access-Control-Allow-Private-Network', 'true')
                self.send_header('Content-Length', '0')
                self.end_headers()
            def allowed(self):
                return self.path == '/mixes' and self.headers.get('Origin') == ORIGIN
            def do_OPTIONS(self): self.reply(204 if self.allowed() else 403)
            def do_POST(self):
                if not self.allowed():
                    self.reply(403); return
                try:
                    size = int(self.headers.get('Content-Length', 0))
                    if not 0 < size <= 2 * 1024 * 1024: raise ValueError('Invalid size')
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
