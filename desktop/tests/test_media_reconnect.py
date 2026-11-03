"""Exercise the real transport over Unix sockets without restarting playback."""
import json
from pathlib import Path
import select
import socket
import subprocess
import sys
import tempfile
import unittest

CLIENT = Path(__file__).resolve().parents[2] / 'system/apps/media'


class ReconnectTests(unittest.TestCase):
    def read_event(self, process):
        self.assertTrue(select.select([process.stdout], [], [], 4)[0], 'transport timed out')
        return json.loads(process.stdout.readline())

    def test_restart_fragmented_messages_and_clean_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / 'player.sock')
            with socket.socket(socket.AF_UNIX) as server:
                server.bind(path)
                server.listen()
                server.settimeout(4)
                code = ('import sys; sys.path.insert(0, sys.argv[1]); '
                        'from menu_client import relay; '
                        'raise SystemExit(relay(sys.argv[2], 0, sys.stdout.buffer, .05))')
                process = subprocess.Popen([sys.executable, '-u', '-c', code, str(CLIENT), path],
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, bufsize=0)
                try:
                    first, _ = server.accept()
                    with first:
                        first.sendall(b'{"event":"rea')
                        first.sendall(b'dy"}\n')
                        self.assertEqual(self.read_event(process)['event'], 'ready')
                        process.stdin.write(b'{"action":"pause"}\n')
                        first.settimeout(4)
                        self.assertEqual(first.recv(4096), b'{"action":"pause"}\n')
                        first.sendall(b'{"event":"incomplete')
                    self.assertEqual(self.read_event(process)['event'], 'connection-lost')
                    second, _ = server.accept()
                    with second:
                        second.sendall(b'{"event":"ready"}\n')
                        self.assertEqual(self.read_event(process)['event'], 'ready')
                        # No command from the old session is replayed.
                        self.assertFalse(select.select([second], [], [], .15)[0])
                        process.stdin.close()
                        self.assertEqual(process.wait(timeout=4), 0)
                        self.assertEqual(process.stderr.read(), b'')
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    process.stdout.close()
                    process.stderr.close()

    def test_can_close_while_service_is_unavailable(self):
        with tempfile.TemporaryDirectory() as folder:
            code = ('import sys; sys.path.insert(0, sys.argv[1]); '
                    'from menu_client import relay; '
                    'raise SystemExit(relay(sys.argv[2], 0, sys.stdout.buffer, .05))')
            result = subprocess.run([sys.executable, '-u', '-c', code, str(CLIENT), folder+'/missing'],
                                    input=b'', capture_output=True, timeout=4)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, b'')
            self.assertEqual(json.loads(result.stdout)['event'], 'connection-lost')
