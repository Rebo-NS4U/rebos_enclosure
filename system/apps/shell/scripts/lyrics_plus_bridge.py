#!/usr/bin/env python3
"""Receive lyrics only from Spotify's local Spicetify extension; emit JSON to QML."""
import json
import math
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 19837
ORIGIN = 'https://xpui.app.spotify.com'


def normalize(data):
    if not isinstance(data, dict) or not re.fullmatch(r'spotify:track:[A-Za-z0-9]{22}', str(data.get('uri', ''))):
        raise ValueError('Invalid track URI')
    rows = data.get('lines')
    if not isinstance(rows, list) or len(rows) > 3000:
        raise ValueError('Invalid lines')
    result = []
    synced = data.get('synced') is True
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('text'), str):
            raise ValueError('Invalid line')
        item = {'text': row['text'][:10000]}
        if synced:
            time = float(row.get('time', -1))
            if not math.isfinite(time) or time < 0:
                raise ValueError('Invalid time')
            item['time'] = time
        result.append(item)
    if synced:
        result.sort(key=lambda row: row['time'])
    return {'uri': data['uri'], 'lines': result, 'synced': synced,
            'provider': 'Lyrics Plus · ' + str(data.get('provider', 'Spotify'))[:80]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, status):
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', ORIGIN)
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def allowed(self):
        return self.path == '/lyrics' and self.headers.get('Origin') == ORIGIN

    def do_OPTIONS(self):
        self.reply(204 if self.allowed() else 403)

    def do_POST(self):
        if not self.allowed():
            self.reply(403)
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 512 * 1024:
                raise ValueError('Invalid size')
            data = normalize(json.loads(self.rfile.read(size)))
        except (ValueError, TypeError, OverflowError):
            self.reply(400)
            return
        print(json.dumps(data, ensure_ascii=True), flush=True)
        self.reply(204)

    def setup(self):
        super().setup()
        self.connection.settimeout(5)


if __name__ == '__main__':
    HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
