"""Check the greeting's terminal bounds and safe, independent rendering."""
import io
import os
from pathlib import Path
import re
import runpy
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[3] / 'system/bin/terminal-bonsai'
BONSAI = runpy.run_path(str(SOURCE))
SGR = re.compile(r'\x1b\[[0-9;]*m')


class BonsaiTests(unittest.TestCase):
    def test_all_sizes_and_variations_fit(self):
        for columns, rows in ((36, 18), (40, 22), (44, 24), (80, 30), (160, 50)):
            for seed in range(4):
                with self.subTest(columns=columns, rows=rows, seed=seed):
                    output = BONSAI['render'](columns, rows, seed)
                    plain = SGR.sub('', output)
                    self.assertNotIn('\x1b', plain)
                    self.assertLessEqual(len(plain.splitlines()), rows)
                    self.assertLessEqual(max(map(len, plain.splitlines())), columns)
                    self.assertIn('▀', plain)
                    self.assertTrue(output.endswith('\033[0m\n\n'))

    def test_small_terminals_stay_quiet(self):
        self.assertEqual(BONSAI['render'](35, 30), '')
        self.assertEqual(BONSAI['render'](80, 17), '')

    def test_palette_cannot_inject_controls(self):
        normal = BONSAI['render'](40, 22)
        self.assertEqual(normal, BONSAI['render'](40, 22, palette={'tertiary': '\x1b[2J', 'secondary': []}))
        self.assertEqual(normal, BONSAI['render'](40, 22, palette=[]))

    def test_piped_output_stays_quiet(self):
        with patch('sys.stdout', io.StringIO()) as output, patch.dict(os.environ, TERM='xterm-256color'):
            BONSAI['main']()
            self.assertEqual(output.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
