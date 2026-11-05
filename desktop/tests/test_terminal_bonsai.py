"""Behavior checks for the procedural greeting, without requiring a desktop."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import pty
import subprocess
import unittest

SOURCE = Path(__file__).resolve().parents[2] / 'system/bin/terminal-bonsai'
loader = importlib.machinery.SourceFileLoader('terminal_bonsai', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
bonsai = importlib.util.module_from_spec(spec)
loader.exec_module(bonsai)


class BonsaiTests(unittest.TestCase):
    def test_seed_replay_and_variety(self):
        signatures = set()
        for seed in range(40):
            tree = bonsai.Tree(48, 18, seed)
            signatures.add(str(tree.cells(1)))
            self.assertEqual(tree.cells(1), bonsai.Tree(48, 18, seed).cells(1))
        self.assertEqual(len(signatures), 40)

    def test_growth_starts_small_and_gains_detail(self):
        tree = bonsai.Tree(48, 18, 42)
        count = lambda age: sum(cell[0] != ' ' for row in tree.cells(age) for cell in row)
        self.assertLess(count(0), 8)
        self.assertGreater(count(.5), count(.1))
        self.assertGreater(count(1), count(.5))
        self.assertGreater(count(1), 100)

    def test_frame_fits_supported_terminal_sizes(self):
        for columns, rows in ((36, 18), (44, 24), (80, 24), (120, 40)):
            for seed in range(20):
                tree = bonsai.Tree(min(64, columns - 8), min(22, rows - 9), seed)
                lines = bonsai.render(tree, 1, bonsai.PALETTE, columns, True).splitlines()
                self.assertLess(len(lines), rows)
                self.assertTrue(all(len(line) <= columns for line in lines))
                self.assertEqual(len(set(map(len, lines))), 1)

    def test_redirected_greeting_is_quiet_but_plain_is_exportable(self):
        self.assertEqual(subprocess.check_output([str(SOURCE)], env={**os.environ, 'TERM': 'xterm'}), b'')
        art = subprocess.check_output([str(SOURCE), '--plain', '--seed', '42'])
        self.assertIn('╭'.encode(), art)
        self.assertNotIn(b'\x1b', art)

    def test_animation_uses_scrollback_and_leaves_input_unread(self):
        master, slave = pty.openpty()
        try:
            proc = subprocess.Popen([str(SOURCE), '--seed', '42'], stdin=slave, stdout=slave,
                                    stderr=slave, env={**os.environ, 'TERM': 'xterm', 'COLUMNS': '80', 'LINES': '24'})
            os.write(master, b'queued-command\n')
            output = b''
            # Consume while running so the PTY output buffer cannot block growth.
            import select
            import time
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    output += os.read(master, 65536)
                elif proc.poll() is not None:
                    break
            self.assertEqual(proc.wait(timeout=1), 0)
            self.assertIn(b'\x1b[20A', output)
            self.assertNotIn(b'\x1b[?1049', output)
            self.assertEqual(os.read(slave, 100), b'queued-command\n')
        finally:
            os.close(master)
            os.close(slave)


if __name__ == '__main__':
    unittest.main()
