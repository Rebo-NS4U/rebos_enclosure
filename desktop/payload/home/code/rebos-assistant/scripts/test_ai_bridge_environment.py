"""Exercise desktop environment propagation at the real child-process boundary."""
import asyncio
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import ai_bridge


class DesktopEnvironmentTests(unittest.IsolatedAsyncioTestCase):
    async def launch(self, **extra):
        bridge = ai_bridge.Bridge()
        frame = dict(command=[sys.executable, '-c',
                              'import json,os; print(json.dumps(dict(os.environ)))'],
                     cwd=str(Path(__file__).parent), **extra)
        try:
            await bridge.start(frame)
            await asyncio.gather(*bridge.tasks)
            event = next(event for event in bridge.events if event['bridge'] == 'acp')
            return event['message']
        finally:
            await bridge.stop()

    async def test_desktop_connections_override_stale_service_environment(self):
        with patch.dict(os.environ, {'DISPLAY': ':old', 'WAYLAND_DISPLAY': 'old'}, clear=True):
            result = await self.launch(path='/usr/bin', desktopEnvironment={
                'DISPLAY': ':1', 'WAYLAND_DISPLAY': 'wayland-1',
                'XDG_RUNTIME_DIR': '/run/user/1000',
                'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/run/user/1000/bus',
                'NIRI_SOCKET': '/run/user/1000/niri.test.sock',
                'OPENAI_API_KEY': 'must-not-forward', 'LD_PRELOAD': 'must-not-forward',
                'HOME': '/must-not-override'})
        self.assertEqual(result['DISPLAY'], ':1')
        self.assertEqual(result['WAYLAND_DISPLAY'], 'wayland-1')
        self.assertEqual(result['XDG_RUNTIME_DIR'], '/run/user/1000')
        self.assertEqual(result['DBUS_SESSION_BUS_ADDRESS'], 'unix:path=/run/user/1000/bus')
        self.assertEqual(result['NIRI_SOCKET'], '/run/user/1000/niri.test.sock')
        self.assertEqual(result['PATH'], '/usr/bin')
        for key in ('OPENAI_API_KEY', 'LD_PRELOAD', 'HOME'):
            self.assertNotIn(key, result)

    async def test_old_clients_and_invalid_values_preserve_service_environment(self):
        with patch.dict(os.environ, {'DISPLAY': ':service'}, clear=True):
            self.assertEqual((await self.launch())['DISPLAY'], ':service')
            for value in ('', None, 12, 'bad\0value'):
                result = await self.launch(desktopEnvironment={'DISPLAY': value})
                self.assertEqual(result['DISPLAY'], ':service')

    async def test_malformed_environment_is_rejected_before_launch(self):
        with self.assertRaisesRegex(ValueError, 'Invalid desktop environment'):
            await self.launch(desktopEnvironment=['DISPLAY'])


if __name__ == '__main__':
    unittest.main()
