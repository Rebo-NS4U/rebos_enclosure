"""Preserve bounded DNS validation caching without caching unsafe answers."""
import importlib.util
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/media/stream_relay.py'
spec = importlib.util.spec_from_file_location('dns_relay', SOURCE)
relay_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay_module)


class RelayDnsCacheTests(unittest.TestCase):
    def setUp(self):
        self.relay = relay_module.StreamRelay()
        self.addCleanup(self.relay.close)
        self.public = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))]

    def test_success_is_reused_only_for_thirty_seconds(self):
        with patch.object(relay_module.socket, 'getaddrinfo', return_value=self.public) as lookup, \
             patch.object(relay_module.time, 'monotonic', return_value=10) as clock:
            self.relay.validate('https://example.test/one')
            clock.return_value = 20
            self.relay.validate('https://example.test/two')
            self.assertEqual(lookup.call_count, 1)
            clock.return_value = 41
            self.relay.validate('https://example.test/three')
            self.assertEqual(lookup.call_count, 2)

    def test_private_answer_is_never_cached_and_http_stays_rejected(self):
        private = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]
        with patch.object(relay_module.socket, 'getaddrinfo', return_value=private) as lookup:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, 'Public'):
                    self.relay.validate('https://example.test/video')
            self.assertEqual(lookup.call_count, 2)
            self.assertEqual(self.relay.validated_hosts, {})
            with self.assertRaisesRegex(ValueError, 'HTTPS'):
                self.relay.validate('http://example.test/video')

    def test_cache_has_at_most_256_hosts(self):
        with patch.object(relay_module.socket, 'getaddrinfo', return_value=self.public):
            for index in range(257):
                self.relay.validate(f'https://host{index}.example.test/video')
            self.assertEqual(len(self.relay.validated_hosts), 256)
            self.assertNotIn(('host0.example.test', 443), self.relay.validated_hosts)
