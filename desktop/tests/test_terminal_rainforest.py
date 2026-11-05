"""Viewport, theme and shell-safety checks for the rainforest greeting."""
import importlib.machinery
import importlib.util
from pathlib import Path
import re
import subprocess
import unittest

SOURCE = Path(__file__).resolve().parents[2] / 'system/bin/terminal-rainforest'
loader = importlib.machinery.SourceFileLoader('rainforest', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
rainforest = importlib.util.module_from_spec(spec)
loader.exec_module(rainforest)


class RainforestTests(unittest.TestCase):
    def test_viewports(self):
        for columns, rows in ((24, 10), (40, 18), (80, 24), (160, 48), (300, 80)):
            for seed in range(12):
                picture = rainforest.render(columns, rows, seed, plain=True)
                lines = picture.splitlines()
                self.assertLessEqual(len(lines), min(20, max(6, rows//2)))
                self.assertTrue(all(len(line) < columns for line in lines))
                self.assertTrue(any(char in picture for char in '&%#@'))
                self.assertNotIn('\033', picture)
                self.assertNotIn('█', picture)
                self.assertNotIn('▄', picture)

    def test_seed_and_layers(self):
        self.assertEqual(rainforest.forest(80, 10, 42), rainforest.forest(80, 10, 42))
        self.assertNotEqual(rainforest.forest(80, 10, 42), rainforest.forest(80, 10, 43))
        self.assertEqual({layer for row in rainforest.forest(80, 12, 42)
                          for glyph, layer in row}, {0, 1, 2, 3})

    def test_terminal_theme_and_no_cursor_controls(self):
        picture = rainforest.render(80, 24, 42)
        escapes = re.findall(r'\033\[[0-9;]*[A-Za-z]', picture)
        self.assertTrue(escapes)
        self.assertTrue(all(code in (*rainforest.COLORS, rainforest.RESET) for code in escapes))
        self.assertEqual(re.sub(r'\033\[[0-9;]*m', '', picture),
                         rainforest.render(80, 24, 42, plain=True))

    def test_small_and_redirected_greetings_are_quiet(self):
        self.assertEqual(rainforest.render(23, 24), '')
        self.assertEqual(rainforest.render(80, 9), '')
        result = subprocess.run([str(SOURCE)], capture_output=True, check=True)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(result.stderr, b'')


if __name__ == '__main__':
    unittest.main()
