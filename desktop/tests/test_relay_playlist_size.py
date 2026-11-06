"""Large HLS manifests remain playable with a bounded relay read."""
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/media/stream_relay.py'
spec = importlib.util.spec_from_file_location('playlist_relay', SOURCE)
relay_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay_module)


class RelayPlaylistTests(unittest.TestCase):
    def setUp(self):
        self.relay = relay_module.StreamRelay(allow_local=True)
        self.addCleanup(self.relay.close)
        self.url = self.relay.register('http://127.0.0.1:9999/index.m3u8')

    def upstream(self, payload):
        upstream = io.BytesIO(payload)
        upstream.url = 'http://127.0.0.1:9999/index.m3u8'
        upstream.headers = {'Content-Type': 'application/vnd.apple.mpegurl'}
        return upstream

    def test_large_youtube_playlist_is_rewritten(self):
        payload = b'#EXTM3U\n#' + b'x' * 4_563_314 + b'\nsegment.ts\n'
        with patch.object(self.relay.opener, 'open', return_value=self.upstream(payload)):
            with urlopen(self.url, timeout=5) as response:
                result = response.read()
                self.assertEqual(response.status, 200)
        self.assertTrue(result.startswith(b'#EXTM3U\n'))
        self.assertNotIn(b'segment.ts', result)
        self.assertIn(b'/media/2', result)

    def test_limit_accepts_exact_size_and_rejects_one_byte_more(self):
        for extra in (0, 1):
            payload = b'#EXTM3U\n#' + b'x' * (relay_module.MAX_PLAYLIST_BYTES - 9 + extra)
            with self.subTest(extra=extra), patch.object(self.relay.opener, 'open', return_value=self.upstream(payload)):
                if extra:
                    with self.assertRaises(HTTPError) as error:
                        urlopen(self.url, timeout=5)
                    self.assertEqual(error.exception.code, 502)
                    error.exception.close()
                else:
                    with urlopen(self.url, timeout=5) as response:
                        self.assertEqual(response.status, 200)
                        self.assertTrue(response.read().startswith(b'#EXTM3U'))
