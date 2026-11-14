"""An explicit shutdown releases the service; a UI detach does not."""
import asyncio
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('shutdown_bridge', ROOT / 'system/apps/assistant/scripts/ai_bridge.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class ShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_exits_server_and_removes_socket(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bridge.sock'
            task = asyncio.create_task(bridge.serve(path))
            try:
                for _ in range(100):
                    if path.exists():
                        break
                    await asyncio.sleep(.01)
                reader, writer = await asyncio.open_unix_connection(str(path))
                # A connection disappearing before attach must not stop service.
                writer.close()
                await writer.wait_closed()
                await asyncio.sleep(.05)
                self.assertFalse(task.done())
                reader, writer = await asyncio.open_unix_connection(str(path))
                writer.write(bridge.encode({'bridge': 'shutdown'}))
                await writer.drain()
                await asyncio.wait_for(task, 2)
                writer.close()
                await writer.wait_closed()
                self.assertFalse(path.exists())
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
