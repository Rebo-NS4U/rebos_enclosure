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
        self.assertIn('╭─────────────────────╮', image)
        self.assertLessEqual(len(image.splitlines()), 26)
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
            shoots = [cell for cell in cells if cell[4].startswith('shoot')]
            self.assertFalse(any(cell[3] in '│╰╯' for cell in shoots))
            self.assertTrue(any(cell[3] in '╱╲' for cell in shoots))
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

    def test_starter_leaves_rise_then_extend_with_first_branches(self):
        for seed in range(24):
            def tips(day):
                return [(x, y) for x, y, _, _, ink in bonsai.juvenile_foliage(day, seed)
                        if ink.startswith('shoot_tip')]
            self.assertLess(tips(3)[0][1], tips(0)[0][1])
            left_start, right_start = tips(12)
            left_end, right_end = tips(22)
            self.assertLess(left_end[0], left_start[0])
            self.assertGreater(right_end[0], right_start[0])
            main_wood = [(x, y) for x, y, _, _, ink in bonsai.specimen(seed, 22)
                         if not ink.startswith('leaf')]
            for x, y in (left_end, right_end):
                self.assertTrue(any(max(abs(x-wx), abs(y-wy)) <= 1
                                    for wx, wy in main_wood))
            for day in (0, 3, 7, 14, 22):
                cells = bonsai.juvenile_foliage(day, seed)
                self.assertLessEqual(sum(cell[4].startswith('leaf') for cell in cells), 4)

    def test_supported_foliage_intersection_stays_visible(self):
        canvas = [[(' ', '') for _ in range(8)] for _ in range(8)]
        for y in (2, 3, 4):
            canvas[y][2] = ('│', 'wood')
        canvas[1][2] = ('●', 'leaf1')
        canvas[2][3] = ('◆', 'leaf2')
        canvas[2][6] = ('╱', 'wood')
        canvas[1][6] = ('●', 'leaf1')
        canvas[2][7] = ('◆', 'leaf2')
        bonsai.cover_crown_wood(canvas)
        self.assertEqual(canvas[2][2], ('│', 'wood'))
        self.assertEqual(canvas[2][6], (' ', ''))

    def test_pushed_pot_patterns_are_stable_and_fit(self):
        self.assertEqual(len(bonsai.POT_MOTIFS), 16)
        designs = set()
        for seed in range(100):
            rows = bonsai.pot_rows(seed)
            self.assertEqual(rows, bonsai.pot_rows(seed))
            self.assertEqual([len(row) for row in rows], [23] * 4)
            designs.add(rows)
        self.assertGreaterEqual(len(designs), 16)

    def test_animation_completes_and_key_skip_restores_terminal(self):
        import fcntl
        import pty
        import select
        import struct
        import termios
        import time
        for skip in (False, True, "signal"):
            with tempfile.TemporaryDirectory() as directory:
                master, slave = pty.openpty()
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
                original = termios.tcgetattr(slave)
                env = {**os.environ, 'TERM': 'xterm-256color', 'XDG_STATE_HOME': directory}
                env.pop('REDUCE_MOTION', None)
                process = subprocess.Popen([str(SOURCE), '--animate', '--seed', '42',
                    '--duration', '10' if skip else '.15'],
                    stdin=slave, stdout=slave, stderr=slave, env=env)
                output = b''
                sent = False
                began = time.monotonic()
                try:
                    while time.monotonic() - began < 4:
                        if select.select([master], [], [], .05)[0]:
                            output += os.read(master, 65536)
                        if skip and not sent and b'\033[26A' in output:
                            if skip == 'signal':
                                import signal
                                process.send_signal(signal.SIGTERM)
                            else:
                                os.write(master, b' ')
                            sent = True
                        if process.poll() is not None:
                            while select.select([master], [], [], 0)[0]:
                                output += os.read(master, 65536)
                            break
                    self.assertEqual(process.poll(), 0)
                    self.assertEqual(termios.tcgetattr(slave), original)
                    import re
                    plain = re.sub(rb'\x1b\[[0-9;]*m', b'', output)
                    self.assertIn('╭─────────────────────╮'.encode(), plain)
                    self.assertGreaterEqual(output.count(b'\033[26A'), 2)
                    self.assertIn(b'\033[?25h', output)
                    self.assertNotIn(b'Traceback', output)
                    self.assertEqual(list(Path(directory).iterdir()), [])
                    if skip:
                        self.assertTrue(sent)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    os.close(master)
                    os.close(slave)

    def test_frame_fits_and_keeps_animation_height(self):
        for columns in (59, 80, 100):
            for day in (0, 7, 30):
                image = bonsai.render(day, 42, False, columns,
                                     ['#85b470'] * 3, fixed_height=True)
                rows = image.splitlines()
                self.assertEqual(len(rows), 26)
                self.assertIn('╔', rows[0])
                self.assertIn('╝', rows[-1])
                self.assertEqual(len({len(row) for row in rows}), 1)
                self.assertTrue(all(len(row) <= columns for row in rows))
                self.assertNotIn('\033', image)

    def test_theme_updates_without_recoloring_wood_or_rewriting_state(self):
        import json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            state = base / 'state/bonsai-grow/tree.json'
            state.parent.mkdir(parents=True)
            original = json.dumps({'seed': 123, 'palette': ['#ff0000'] * 3})
            state.write_text(original)
            cache = base / 'cache/rebos_shell/effective-palette.json'
            cache.parent.mkdir(parents=True)
            with patch.dict(os.environ, {'XDG_STATE_HOME': str(base/'state'),
                                         'XDG_CACHE_HOME': str(base/'cache')}):
                for accent in ('#00ff00', '#0000ff'):
                    cache.write_text(json.dumps(dict.fromkeys(
                        ('primary', 'secondary', 'tertiary'), accent)))
                    seed, palette = bonsai.preview_identity(None)
                    self.assertEqual(seed, 123)
                    self.assertEqual(palette, [accent] * 3)
                    image = bonsai.render(30, seed, True, 80, palette)
                    self.assertIn('\033[38;2;185;158;119m', image)
                    self.assertIn('\033[38;2;151;135;112m', image)
                    self.assertEqual(state.read_text(), original)

    def test_branch_plans_vary_and_repeat_by_seed(self):
        layouts = set()
        for seed in range(48):
            layout = bonsai.branch_layout(seed)
            self.assertEqual(layout, bonsai.branch_layout(seed))
            layouts.add(tuple((depth, round(x), round(y)) for depth, x, y, born in layout))
            self.assertTrue(all(born >= (depth - 1) / .7 for depth, x, y, born in layout))
        self.assertGreater(len(layouts), 40)

    def test_new_launches_use_fresh_seeds_and_explicit_seed_is_repeatable(self):
        from unittest.mock import patch, Mock
        with patch('sys.stdout', Mock(isatty=lambda: True)), \
             patch('sys.stdin', Mock(isatty=lambda: True)), \
             patch.dict(os.environ, {'TERM': 'xterm-256color'}), \
             patch.object(bonsai.shutil, 'get_terminal_size', return_value=os.terminal_size((100, 40))), \
             patch.object(bonsai.random, 'SystemRandom') as entropy, \
             patch.object(bonsai, 'render', return_value='') as render:
            entropy.return_value.randrange.side_effect = [111, 222]
            for _ in range(2):
                with patch('sys.argv', [str(SOURCE), '--animate', '--plain']):
                    bonsai.main()
            self.assertEqual([call.args[1] for call in render.call_args_list], [111, 222])
            with patch('sys.argv', [str(SOURCE), '--animate', '--plain', '--seed', '42']):
                bonsai.main()
            self.assertEqual(render.call_args.args[1], 42)

    def test_preview_does_not_create_growth_state(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([str(SOURCE), '--preview', '30', '--seed', '42', '--plain'],
                env={**os.environ, 'XDG_STATE_HOME': directory},
                text=True, capture_output=True, check=True)
            self.assertIn('╭─────────────────────╮', result.stdout)
            self.assertNotIn('\033', result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_redirected_greeting_is_quiet(self):
        result = subprocess.run([str(SOURCE)], capture_output=True, check=True)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(result.stderr, b'')


if __name__ == '__main__':
    unittest.main()
