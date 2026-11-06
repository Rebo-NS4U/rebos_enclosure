"""Shared transport preserves shell and assistant protocol capabilities."""
from pathlib import Path
import runpy
import unittest
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).resolve().parents[2]


class BridgeModeTests(unittest.IsolatedAsyncioTestCase):
    def bridge(self, app):
        return runpy.run_path(str(ROOT / 'system/apps' / app / 'scripts/ai_bridge.py'))['Bridge']()

    async def test_only_assistant_advertises_parking(self):
        for app in ('shell', 'assistant'):
            bridge = self.bridge(app)
            bridge.send = Mock()
            bridge.send_attached(None, 0)
            self.assertEqual(bridge.send.call_args.args[0].get('parking', False), app == 'assistant')

    async def test_shell_rejects_park_and_wake(self):
        bridge = self.bridge('shell')
        for command in ('park', 'wake'):
            with self.assertRaisesRegex(ValueError, 'Unknown'):
                await bridge.handle_frame({'bridge': command})

    async def test_reset_restarts_and_shutdown_exits_both_modes(self):
        for app in ('shell', 'assistant'):
            bridge = self.bridge(app)
            bridge.launch = {'command': ['fake'], 'cwd': '/tmp'}
            bridge.stop, bridge.start, bridge.send = AsyncMock(), AsyncMock(), Mock()
            self.assertTrue(await bridge.handle_frame({'bridge': 'reset'}))
            bridge.start.assert_awaited_once_with(bridge.launch)
            self.assertFalse(await bridge.handle_frame({'bridge': 'shutdown'}))
            self.assertEqual(bridge.stop.await_count, 2)

    async def test_assistant_parking_preserves_checkpoint_and_wakes(self):
        bridge = self.bridge('assistant')
        bridge.stop, bridge.start, bridge.send = AsyncMock(), AsyncMock(), Mock()
        bridge.launch = {'command': ['fake']}
        state = {'agentCapabilities': {'loadSession': True}, 'sessionReady': True, 'currentSessionId': 'test'}
        self.assertTrue(await bridge.handle_frame({'bridge': 'park', 'seq': 0, 'state': state}))
        bridge.stop.assert_awaited_once_with(preserve_state=True)
        self.assertTrue(bridge.parked)
        self.assertTrue(await bridge.handle_frame({'bridge': 'wake', 'seq': 1, 'state': state}))
        bridge.start.assert_awaited_once_with(bridge.launch)
        self.assertFalse(bridge.parked)
        self.assertIsNone(bridge.state)

    async def test_busy_assistant_cannot_park(self):
        bridge = self.bridge('assistant')
        bridge.stop, bridge.send = AsyncMock(), Mock()
        state = {'agentCapabilities': {'loadSession': True}, 'sessionReady': True,
                 'currentSessionId': 'test', 'toolRunning': True}
        await bridge.handle_frame({'bridge': 'park', 'seq': 0, 'state': state})
        bridge.stop.assert_not_awaited()
        bridge.send.assert_called_once_with({'bridge': 'park-rejected'})
