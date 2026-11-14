"""A stalled media UI must never stall playback or another UI."""
import json
import socket
import unittest

from backend_server import BackendServer
from client_connection import ClientConnection, SEND_TIMEOUT


class BackpressureTests(unittest.TestCase):
    def setUp(self):
        self.clients = []
        self.peers = []

    def tearDown(self):
        for client in self.clients:
            client.close()
            client.worker.join(3)
        for peer in self.peers:
            peer.close()

    def pair(self):
        output, peer = socket.socketpair()
        output.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        client = ClientConnection(output)
        self.clients.append(client)
        self.peers.append(peer)
        return client, peer

    def test_nonreading_client_cannot_block_other_clients_or_server_lock(self):
        slow, _ = self.pair()
        fast, peer = self.pair()
        server = BackendServer()
        server.clients.update(slow=slow, fast=fast)
        self.assertTrue(slow.send(b'x' * 512000))
        server.send({'event': 'paused', 'paused': True})
        peer.settimeout(1)
        self.assertTrue(json.loads(peer.recv(4096))['paused'])
        with server.lock:
            self.assertIn('paused', server.latest)
        slow.worker.join(SEND_TIMEOUT + 1)
        self.assertFalse(slow.worker.is_alive())
        self.assertTrue(slow.closed.is_set())

    def test_closed_and_oversized_clients_are_removed_without_losing_state(self):
        client, _ = self.pair()
        server = BackendServer()
        server.clients['closed'] = client
        self.assertFalse(client.send(b'x' * (1024 * 1024 + 1)))
        server.send({'event': 'paused', 'paused': False})
        self.assertFalse(server.clients)
        self.assertFalse(server.latest['paused']['paused'])
