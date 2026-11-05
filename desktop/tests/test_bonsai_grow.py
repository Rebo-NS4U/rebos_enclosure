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
                self.assertGreaterEqual(len(leaves), 2)
                self.assertLessEqual(len(leaves), 16)
                self.assertGreaterEqual(len(leaves), previous_count)
                previous_count = len(leaves)
                for x, y, born, glyph, ink in leaves:
                    self.assertLessEqual(born, day)
                    shoots = [cell for cell in cells if cell[4].startswith('shoot')]
                    self.assertTrue(any(max(abs(x - sx), abs(y - sy)) <= 1
                                        for sx, sy, *_ in shoots))
                    self.assertTrue(0 <= x < 57 and 0 <= y < 19)
                image = bonsai.render(day, seed, False, 80, ['#85b470'] * 3)
                self.assertTrue(any(glyph in image for glyph in '◆●•·'))
            self.assertEqual(bonsai.juvenile_foliage(30, seed), [])

    def test_early_leaves_follow_connected_shoot_tips(self):
        for seed in range(24):
            for day in (0, 1, 2, 3, 7, 14, 25):
                cells = bonsai.juvenile_foliage(day, seed)
                shoots = {(x, y) for x, y, _, _, ink in cells if ink.startswith('shoot')}
                reached = {(x, y) for x, y, *_ in bonsai.stem(day, seed)}
                pending = set(shoots)
                while pending:
                    attached = {point for point in pending
                                if any(max(abs(point[0]-x), abs(point[1]-y)) <= 1
                                       for x, y in reached)}
                    self.assertTrue(attached, 'Detached juvenile branch')
                    reached.update(attached)
                    pending.difference_update(attached)
                # Leaves sit at an end, not midway along a continuing branch.
                for x, y, _, _, ink in cells:
                    if not ink.startswith('leaf'):
                        continue
                    neighbors = {(sx, sy) for sx, sy in shoots
                                 if max(abs(sx-x), abs(sy-y)) <= 1}
                    self.assertTrue(neighbors)
                    tips = {(tx, ty) for tx, ty, _, _, tip_ink in cells
                            if tip_ink.startswith('shoot_tip')}
                    self.assertTrue(any(abs(x - tx) + abs(y - ty) == 1
                                        for tx, ty in tips))

    def test_buds_unfold_and_petioles_blend_into_leaf_color(self):
        glyphs = []
        for day in (0, .75, 3):
            cells = bonsai.juvenile_foliage(day, 42)
            first_leaf = next(cell for cell in cells if cell[4].startswith('leaf'))
            glyphs.append(first_leaf[3])
            self.assertTrue(any(cell[3] in '╰╯' for cell in cells))
        self.assertEqual(glyphs, ['·', '•', '●'])
        image = bonsai.render(3, 42, True, 80, ['#00ff00'] * 3)
        # Petioles carry intermediate colors rather than a hard wood/leaf jump.
        self.assertIn('\033[38;2;120;192;77m', image)
        self.assertIn('\033[38;2;56;226;36m', image)


    def test_starting_wood_has_body_and_tapers(self):
        for seed in range(24):
            for day in (0, 3, 7):
                wood = bonsai.stem(day, seed)
                base = {x for x, y, *_ in wood if y == 18}
                self.assertGreaterEqual(len(base), 2)
                tip_y = min(cell[1] for cell in wood)
                self.assertEqual(sum(cell[1] == tip_y for cell in wood), 1)
            # Main branches have bark-filled thickness soon after emergence.
            branch = bonsai.specimen(seed, 14)
            self.assertTrue(any(ink == 'bark' and glyph in '▒╎'
                                for x, y, born, glyph, ink in branch))

    def test_trunks_vary_without_disconnected_rows(self):
        silhouettes = set()
        bend_positions = set()
        for seed in range(48):
            path = bonsai.trunk_path(seed)
            self.assertEqual(path, bonsai.trunk_path(seed))
            self.assertEqual(path[0], 27)
            self.assertEqual(len(path), 15)
            self.assertTrue(all(abs(a - b) <= .951 for a, b in zip(path, path[1:])))
            silhouettes.add(tuple(round(x) for x in path))
            bend_positions.add(max(range(1, 14), key=lambda i: abs(path[i] - 27)))
        self.assertGreater(len(silhouettes), 40)
        self.assertGreater(len(bend_positions), 3)

    def test_foliage_hides_sticks_without_increasing_leaf_count(self):
        canvas = [[(' ', '') for _ in range(7)] for _ in range(7)]
        canvas[2][2] = ('╱', 'wood')
        canvas[1][2] = ('●', 'leaf1')
        canvas[2][3] = ('◆', 'leaf2')
        canvas[5][2] = ('│', 'wood')
        bonsai.cover_crown_wood(canvas)
        self.assertEqual(canvas[2][2], (' ', ''))
        self.assertEqual(canvas[5][2], ('│', 'wood'))
        self.assertEqual(sum(ink.startswith('leaf') for row in canvas for _, ink in row), 2)

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
