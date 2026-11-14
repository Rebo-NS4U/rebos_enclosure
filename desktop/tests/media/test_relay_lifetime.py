"""Exercise live route ownership and atomic HLS admission under capacity pressure."""
import http.server
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit
from urllib.request import urlopen

import stream_relay
import vlc_session
from menu_backend import Engine
from stream_relay import StreamRelay


class RelayLifetimeTests(unittest.TestCase):
    def setUp(self):
        class Origin(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                data = b'video bytes'
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        self.origin = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Origin)
        threading.Thread(target=self.origin.serve_forever, daemon=True).start()
        self.relay = StreamRelay(allow_local=True)
        self.base = f'http://127.0.0.1:{self.origin.server_port}/'
        self.addCleanup(self.origin.server_close)
        self.addCleanup(self.origin.shutdown)
        self.addCleanup(self.relay.close)

    def fetch(self, url):
        with urlopen(url, timeout=2) as response:
            self.assertEqual(response.status, 200)
            return response.read()

    def test_recently_read_source_survives_unrelated_route_pressure(self):
        with patch('stream_relay.MAX_ROUTES', 4):
            active = self.relay.register(self.base + 'active.mp4')
            for i in range(10):
                self.fetch(active)
                self.relay.register(self.base + f'other-{i}')
            self.fetch(active)
            self.assertLessEqual(len(self.relay.sources), 4)

    def test_paused_player_owns_routes_until_release(self):
        owner = object()
        with patch('stream_relay.MAX_ROUTES', 4):
            active = self.relay.register(self.base + 'paused.mp4')
            with self.relay.lifetime.playback(owner, [active]):
                pass
            # No reads are necessary while a paused player owns the source.
            for i in range(10):
                self.relay.register(self.base + f'other-{i}')
            self.assertTrue(self.relay.lifetime.available(active))
            self.relay.lifetime.release(owner)
            for i in range(4):
                self.relay.register(self.base + f'replacement-{i}')
            self.assertFalse(self.relay.lifetime.available(active))

    def test_manifest_routes_are_admitted_together_and_kept_with_the_root(self):
        with patch('stream_relay.MAX_ROUTES', 4):
            root = self.relay.register(self.base + 'master')
            path = urlsplit(root).path
            playlist = '#EXTM3U\nseg1\nseg2\nseg3\n'
            rewritten = self.relay.rewrite_for(path, playlist, self.base + 'master', self.relay.sources[path])
            children = rewritten.splitlines()[1:]
            before = set(self.relay.sources)
            with self.relay.lifetime.playback(self, [root]):
                pass
            with self.assertRaisesRegex(ValueError, 'capacity'):
                self.relay.register(self.base + 'prefetch')
            with self.assertRaisesRegex(ValueError, 'capacity'):
                self.relay.rewrite_for(path, playlist + 'seg4\n', self.base + 'master', self.relay.sources[path])
            self.assertEqual(set(self.relay.sources), before)
            for child in children:
                self.fetch(child)
            self.fetch(root)
            self.relay.lifetime.release(self)

    def test_equivalent_header_case_and_default_agent_reuse_a_route(self):
        first = self.relay.register(self.base + 'same', {'referer': 'https://example.com/'})
        second = self.relay.register(self.base + 'same', {'Referer': 'https://example.com/', 'User-Agent': 'Mozilla/5.0'})
        self.assertEqual(first, second)

    def test_release_during_load_does_not_resurrect_an_owner(self):
        owner = object()
        route = self.relay.register(self.base + 'closed')
        with self.relay.lifetime.playback(owner, [route]):
            self.relay.lifetime.release(owner)
        self.assertNotIn(owner, self.relay.lifetime.owners)

    def test_vlc_load_failure_retains_the_previous_source_and_close_releases_it(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(stream_relay, '_RELAY', self.relay):
            session = vlc_session.VlcSession.__new__(vlc_session.VlcSession)
            session.audio_normalization = False
            session.generation = 0
            session.closed = threading.Event()
            session.process = Mock()
            session.process.poll.return_value = 0
            session.logpath = Path(directory) / 'vlc.log'
            session.logpath.touch()
            session.api = Mock()
            session.public_stream = lambda url, referer: url
            old = self.relay.register(self.base + 'old')
            session.apply(['load', [old, '', '', ''], 'Old', False, False])
            previous = self.relay.lifetime.owners[session].copy()
            new = self.relay.register(self.base + 'new')
            session.api.side_effect = RuntimeError('Player refused replacement')
            with self.assertRaises(RuntimeError):
                session.apply(['load', [new, '', '', ''], 'New', False, False])
            self.assertEqual(self.relay.lifetime.owners[session], previous)
            session.close()
            self.assertNotIn(session, self.relay.lifetime.owners)

    def test_expired_resolved_link_is_resolved_again(self):
        key = ('show', '1', 'sub', 'best')
        with patch('stream_relay.MAX_ROUTES', 1), patch.object(stream_relay, '_RELAY', self.relay):
            old = self.relay.register(self.base + 'old')
            self.relay.register(self.base + 'new')
            engine = Engine.__new__(Engine)
            engine.resolved = {key: (time.monotonic(), [old, '', '', ''])}
            engine.resolving = {}
            engine.background = Mock()
            done = Mock()
            engine.resolve(key, done, Mock())
            done.assert_not_called()
            engine.background.assert_called_once()
