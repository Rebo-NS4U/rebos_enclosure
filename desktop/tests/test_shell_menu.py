"""Exercise the real private selection transport, including cancellation and reconnect."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ShellMenuTests(unittest.TestCase):
    def test_selection_cancel_busy_and_reconnect(self):
        with tempfile.TemporaryDirectory() as runtime:
            env = dict(os.environ, XDG_RUNTIME_DIR=runtime)
            server = subprocess.Popen(['python3', str(ROOT / 'system/apps/shell/scripts/menu_broker.py')],
                                      env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            try:
                path = Path(runtime) / 'rebos-shell-menu.sock'
                for _ in range(100):
                    if path.exists():
                        break
                    time.sleep(.01)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                for selection in ('one $literal', None, 'two'):
                    client = subprocess.Popen([str(ROOT / 'system/bin/rebos-menu'), '--prompt', 'Test'], env=env,
                                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                    client.stdin.write('one $literal\ntwo\n')
                    client.stdin.close()
                    request = json.loads(server.stdout.readline())
                    self.assertEqual(request['lines'], ['one $literal', 'two'])
                    with socket.socket(socket.AF_UNIX) as busy:
                        busy.connect(str(path))
                        busy.sendall(b'{"lines":[]}\n')
                        self.assertEqual(json.loads(busy.recv(100))['selection'], None)
                    server.stdin.write(json.dumps({'selection': selection}) + '\n')
                    server.stdin.flush()
                    self.assertEqual(client.stdout.read(), '' if selection is None else selection + '\n')
                    self.assertEqual(client.wait(timeout=3), 1 if selection is None else 0)
                    client.stdout.close()
            finally:
                server.stdin.close()
                server.wait(timeout=3)
                server.stdout.close()
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
