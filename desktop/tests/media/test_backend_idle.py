"""Idle shutdown must release memory without interrupting playback."""
import unittest
from unittest.mock import Mock, patch

import backend_server
from backend_server import BackendServer


class BackendIdleTests(unittest.TestCase):
    def setUp(self):
        self.server = BackendServer()
        self.server.loop = Mock()
        self.engine = Mock(player=None, download_active=False)
        self.patch = patch.object(backend_server.backend, 'engine', self.engine)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def check_at(self, when):
        with patch.object(backend_server.time, 'monotonic', return_value=when):
            self.server.check_idle()

    def test_idle_exits_only_after_grace_period(self):
        self.check_at(10)
        self.check_at(14)
        self.server.loop.quit.assert_not_called()
        self.check_at(15)
        self.server.loop.quit.assert_called_once()

    def test_connected_ui_resets_idle_countdown(self):
        self.check_at(10)
        self.server.clients['ui'] = Mock()
        self.check_at(20)
        self.server.clients.clear()
        self.check_at(30)
        self.check_at(34)
        self.server.loop.quit.assert_not_called()
        self.check_at(35)
        self.server.loop.quit.assert_called_once()

    def test_live_or_paused_player_survives_without_ui(self):
        self.engine.player = Mock()
        self.engine.player.poll.return_value = None
        self.check_at(10)
        self.check_at(100)
        self.server.loop.quit.assert_not_called()
        self.engine.player.poll.return_value = 0
        self.check_at(101)
        self.check_at(106)
        self.server.loop.quit.assert_called_once()

    def test_download_keeps_service_alive(self):
        self.engine.download_active = True
        self.check_at(10)
        self.check_at(30)
        self.server.loop.quit.assert_not_called()
        self.engine.download_active = False
        self.check_at(31)
        self.check_at(36)
        self.server.loop.quit.assert_called_once()
