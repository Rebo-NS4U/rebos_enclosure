"""Reject DNS rebinding at connect time and preserve HTTPS hostname verification."""
import socket
import unittest
from unittest.mock import Mock, patch
from urllib.request import HTTPSHandler, ProxyHandler

from relay_transport import PublicHTTPSConnection, PublicHTTPSHandler, public_connection
from stream_relay import StreamRelay


class RelayTransportTests(unittest.TestCase):
    def setUp(self):
        self.public = (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))
        self.private = (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))

    def test_rebinding_after_registration_does_not_connect_to_private_address(self):
        relay = StreamRelay()
        self.addCleanup(relay.close)
        with patch('socket.getaddrinfo', side_effect=[[self.public], [self.private]]), \
                patch('relay_transport.socket.socket') as sockets:
            relay.register('https://media.example/video')
            with self.assertRaisesRegex(ValueError, 'Public'):
                relay.opener.open('https://media.example/video', timeout=2)
            sockets.assert_not_called()

    def test_numeric_destination_is_used_without_a_second_resolution(self):
        with patch('socket.getaddrinfo', return_value=[self.public]) as resolver, \
                patch('relay_transport.socket.socket') as sockets:
            connected = public_connection(('media.example', 443), 3)
            resolver.assert_called_once_with('media.example', 443, type=socket.SOCK_STREAM)
            self.assertIs(connected, sockets.return_value)
            connected.connect.assert_called_once_with(('8.8.8.8', 443))
            connected.settimeout.assert_called_once_with(3)

    def test_tls_uses_original_hostname_and_default_verification(self):
        connection = PublicHTTPSConnection('media.example', timeout=3)
        self.assertTrue(connection._context.check_hostname)
        import ssl
        self.assertEqual(connection._context.verify_mode, ssl.CERT_REQUIRED)
        context = Mock()
        connection._context = context
        with patch('socket.getaddrinfo', return_value=[self.public]), \
                patch('relay_transport.socket.socket') as sockets:
            connection.connect()
            context.wrap_socket.assert_called_once_with(sockets.return_value, server_hostname='media.example')

    def test_all_answers_are_checked_and_failed_connections_are_closed(self):
        for answers in ([], [self.public, self.private]):
            with patch('socket.getaddrinfo', return_value=answers), patch('relay_transport.socket.socket') as sockets:
                with self.assertRaisesRegex(ValueError, 'Public'):
                    public_connection(('media.example', 443), 2)
                sockets.assert_not_called()
        ipv6 = (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('2001:4860:4860::8888', 443, 0, 0))
        first, second = Mock(), Mock()
        first.connect.side_effect = OSError('unreachable')
        with patch('socket.getaddrinfo', return_value=[self.public, ipv6]), \
                patch('relay_transport.socket.socket', side_effect=[first, second]):
            self.assertIs(public_connection(('media.example', 443), 2), second)
            first.close.assert_called_once()
            second.connect.assert_called_once_with(ipv6[4])

    def test_environment_proxy_cannot_replace_public_transport(self):
        with patch.dict('os.environ', {'https_proxy': 'http://127.0.0.1:8080'}):
            relay = StreamRelay()
        self.addCleanup(relay.close)
        self.assertTrue(any(isinstance(handler, PublicHTTPSHandler) for handler in relay.opener.handlers))
        self.assertEqual(sum(isinstance(handler, HTTPSHandler) for handler in relay.opener.handlers), 1)
        self.assertFalse(any(isinstance(handler, ProxyHandler) for handler in relay.opener.handlers))
