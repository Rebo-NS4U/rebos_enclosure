"""Render the real nmtui main menu without making any network changes."""
import fcntl
import os
from pathlib import Path
import pty
import re
import select
import shutil
import struct
import subprocess
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / 'system/bin/nmtui'


class NmtuiColorsTests(unittest.TestCase):
    @unittest.skipUnless(Path('/usr/bin/nmtui').exists() and shutil.which('nmcli'), 'NetworkManager tools required')
    def test_fixed_colors_and_clean_exit(self):
        running = subprocess.run(['nmcli', '-t', '-f', 'RUNNING', 'general'], capture_output=True, text=True)
        if running.returncode or running.stdout.strip() != 'running':
            self.skipTest('A running NetworkManager is required for rendering')
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
        env = dict(os.environ, TERM='xterm-256color', NEWT_COLORS='root=red,red')
        process = subprocess.Popen([str(LAUNCHER)], stdin=slave, stdout=slave, stderr=slave, env=env)
        os.close(slave)
        output = b''
        try:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        output += os.read(master, 65536)
                    except OSError:
                        break
                if b'NetworkManager' in output and b'48;5;252m' in output:
                    break
            os.write(master, b'\x1b')
            process.wait(timeout=3)
            self.assertEqual(process.returncode, 0)
            colors = {int(value) for value in re.findall(rb'\x1b\[(?:38|48);5;(\d+)m', output)}
            self.assertTrue({16, 19, 231, 252}.issubset(colors), output)
            self.assertTrue(all(value >= 16 for value in colors), 'UI must avoid desktop-themed ANSI slots')
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)
            os.close(master)


if __name__ == '__main__':
    unittest.main()
