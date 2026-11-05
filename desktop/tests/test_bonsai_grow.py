"""Regression checks for the restored standalone S-shaped bonsai."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2] / 'system/bin/bonsai-grow'
loader = importlib.machinery.SourceFileLoader('bonsai_grow', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
bonsai = importlib.util.module_from_spec(spec)
loader.exec_module(bonsai)


class BonsaiGrowTests(unittest.TestCase):
    def test_standalone_specimen(self):
        palette = ['#85b470', '#b8ce93', '#67bca3']
        image = bonsai.render(30, 42, False, 80, palette)
        self.assertEqual(image, bonsai.render(30, 42, False, 80, palette))
        self.assertIn('╭─────────────────╮', image)
        self.assertLessEqual(len(image.splitlines()), 24)
        self.assertTrue(all(len(row) <= 80 for row in image.splitlines()))
        self.assertNotEqual(image, bonsai.render(30, 43, False, 80, palette))
        self.assertNotEqual(image, bonsai.render(0, 42, False, 80, palette))

    def test_top_clusters_fill_during_growth(self):
        for seed in range(24):
            def upper_leaves(age):
                return [cell for cell in bonsai.specimen(seed, age)
                        if cell[4].startswith('leaf') and cell[1] <= 5
                        and cell[2] <= age + 1]
            developing = upper_leaves(25)
            mature = upper_leaves(30)
            self.assertGreaterEqual(len(developing), 10)
            self.assertGreaterEqual(len(mature), 60)
            center = 28 + (bonsai.trunk_path(seed)[-1] - 27) * .6
            self.assertGreaterEqual(sum(cell[0] < center for cell in mature), 20)
            self.assertGreaterEqual(sum(cell[0] >= center for cell in mature), 20)
            self.assertGreater(sum(cell[3] in '◆●' for cell in mature), len(mature) // 2)

    def test_leafy_juvenile_stages_are_attached_and_retire(self):
        for seed in range(24):
            previous_count = 0
            for day in (0, 3, 7, 14):
                cells = bonsai.juvenile_foliage(day, seed)
                leaves = [cell for cell in cells if cell[4].startswith('leaf')]
                self.assertGreaterEqual(len(leaves), 6)
                self.assertGreaterEqual(len(leaves), previous_count)
                previous_count = len(leaves)
                stem = bonsai.stem(day, seed)
                for x, y, born, glyph, ink in leaves:
                    self.assertLessEqual(born, day)
                    self.assertTrue(any(abs(x - sx) + abs(y - sy) <= 4
                                        for sx, sy, *_ in stem))
                    self.assertTrue(0 <= x < 57 and 0 <= y < 19)
                image = bonsai.render(day, seed, False, 80, ['#85b470'] * 3)
                self.assertTrue(any(glyph in image for glyph in '◆●•'))
            self.assertEqual(bonsai.juvenile_foliage(30, seed), [])

    def test_preview_does_not_create_growth_state(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([str(SOURCE), '--preview', '30', '--seed', '42', '--plain'],
                env={**os.environ, 'XDG_STATE_HOME': directory},
                text=True, capture_output=True, check=True)
            self.assertIn('╭─────────────────╮', result.stdout)
            self.assertNotIn('\033', result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_redirected_greeting_is_quiet(self):
        result = subprocess.run([str(SOURCE)], capture_output=True, check=True)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(result.stderr, b'')


if __name__ == '__main__':
    unittest.main()
