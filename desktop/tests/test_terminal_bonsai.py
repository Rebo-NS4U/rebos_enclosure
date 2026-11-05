"""Growth clock, stable geometry, saved greetings, and live terminal lifecycle."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import tempfile
import time
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
        self.assertGreater(len(set(round(leaf[2], 4) for leaf in tree.leaves)), 100)
        self.assertTrue(all(0 <= leaf[2] <= 1 for leaf in tree.leaves))

    def test_frame_fits_supported_terminal_sizes(self):
        for columns, rows in ((36, 18), (44, 24), (80, 24), (120, 40)):
            for seed in range(20):
                tree = bonsai.Tree(min(72, columns - 8), min(26, rows - 8), seed)
                for age in (0, .2, .5, 1):
                    lines = bonsai.render(tree, age, bonsai.PALETTE, columns, True).splitlines()
                    self.assertLess(len(lines), rows)
                    self.assertTrue(all(len(line) <= columns for line in lines))
                    self.assertEqual(len(set(map(len, lines))), 1)

    def test_saved_growth_clock_and_explicit_replant(self):
        with tempfile.TemporaryDirectory() as home:
            first = bonsai.load_tree(home, now=1000, seed=42)
            self.assertEqual(bonsai.load_tree(home, now=90000), first)
            self.assertEqual(bonsai.age_at(first, 1000), 0)
            self.assertEqual(bonsai.age_at(first, 1000 + 12*3600), .5)
            self.assertEqual(bonsai.age_at(first, 1000 + 24*3600), 1)
            self.assertEqual(bonsai.age_at(first, 1000 + 30*86400), 1)
            self.assertEqual(bonsai.age_at(first, 0), 0)
            planted = bonsai.load_tree(home, now=90000, new=True, seed=27)
            self.assertEqual(planted['seed'], 27)
            self.assertEqual(bonsai.age_at(planted, 90000), 0)
            path = Path(home) / 'terminal-bonsai/tree.json'
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.write_text('invalid json')
            self.assertEqual(bonsai.load_tree(home, now=95000)['planted'], 95000)

    def test_redirected_greeting_quiet_preview_has_no_state_side_effect(self):
        with tempfile.TemporaryDirectory() as home:
            env = {**os.environ, 'TERM': 'xterm', 'XDG_STATE_HOME': home}
            self.assertEqual(subprocess.check_output([str(SOURCE)], env=env), b'')
            art = subprocess.check_output([str(SOURCE), '--plain', '--seed', '42', '--age', '.5'], env=env)
            self.assertIn('12.0/24h'.encode(), art)
            self.assertNotIn(b'\x1b', art)
            self.assertEqual(list(Path(home).iterdir()), [])

    def test_concurrent_greetings_share_one_seed_and_planting_time(self):
        with tempfile.TemporaryDirectory() as home:
            env = {**os.environ, 'XDG_STATE_HOME': home}
            processes = [subprocess.Popen([str(SOURCE), '--plain'], stdout=subprocess.PIPE, env=env)
                         for _ in range(8)]
            pictures = [proc.communicate(timeout=5)[0] for proc in processes]
            self.assertTrue(all(proc.returncode == 0 for proc in processes))
            self.assertEqual(len(set(pictures)), 1)
            state = json.loads((Path(home) / 'terminal-bonsai/tree.json').read_text())
            self.assertLess(time.time() - state['planted'], 5)

    def test_live_restores_terminal_on_exit_and_greeting_returns_immediately(self):
        for live in (False, True):
            with tempfile.TemporaryDirectory() as home:
                master, slave = pty.openpty()
                proc = None
                try:
                    env = {**os.environ, 'TERM': 'xterm', 'XDG_STATE_HOME': home,
                           'COLUMNS': '80', 'LINES': '24', 'REDUCE_MOTION': '0'}
                    proc = subprocess.Popen([str(SOURCE)] + (['--live'] if live else []),
                                            stdin=slave, stdout=slave, stderr=slave, env=env)
                    os.write(master, b'queued-command\n')
                    output = b''
                    deadline = time.monotonic() + 4
                    stopped = False
                    while time.monotonic() < deadline:
                        if select.select([master], [], [], .05)[0]:
                            output += os.read(master, 65536)
                        elif proc.poll() is not None:
                            break
                        if live and b'/24h' in output and not stopped:
                            proc.send_signal(signal.SIGTERM)
                            stopped = True
                    self.assertEqual(proc.wait(timeout=1), 0)
                    if live:
                        self.assertIn(b'\x1b[?1049h', output)
                        self.assertIn(b'\x1b[?25h\x1b[?1049l', output)
                    else:
                        self.assertNotIn(b'\x1b[?1049', output)
                    self.assertEqual(os.read(slave, 100), b'queued-command\n')
                finally:
                    if proc and proc.poll() is None:
                        proc.kill()
                        proc.wait()
                    os.close(master)
                    os.close(slave)


if __name__ == '__main__':
    unittest.main()
