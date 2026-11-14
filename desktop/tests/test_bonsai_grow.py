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
        self.assertIn('╭──────────┴──────────╮', image)
        self.assertLessEqual(len(image.splitlines()), 26)
        self.assertTrue(all(len(row) <= 80 for row in image.splitlines()))
        self.assertNotEqual(image, bonsai.render(30, 43, False, 80, palette))
        self.assertNotEqual(image, bonsai.render(0, 42, False, 80, palette))

    def test_foliage_dots_stay_on_cluster_edges(self):
        dots = 0
        for seed in range(24):
            for day in (7,14,30):
                plan = bonsai.natural_specimen(seed,day)
                foliage = {(x,y) for x,y,born,glyph,ink in plan if ink.startswith('leaf')}
                wood = {(x,y) for x,y,born,glyph,ink in plan + bonsai.stem(day,seed)
                        if not ink.startswith('leaf')}
                for x,y,born,glyph,ink in plan:
                    if ink.startswith('leaf') and glyph in '•·':
                        dots += 1
                        self.assertNotIn((x,y),wood)
                        self.assertTrue(any((x+dx,y+dy) not in foliage
                                            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1))))
        self.assertGreater(dots,100)

    def test_exposed_wood_has_solid_edges_and_retains_inner_dots(self):
        from unittest.mock import patch
        interior_dots = 0
        for seed in range(24):
            for day in (7,14,30):
                with patch.object(bonsai, 'seat_tree_in_pot', wraps=bonsai.seat_tree_in_pot) as seat:
                    bonsai.render(day,seed)
                    canvas = seat.call_args.args[0]
                occupied = {(x,y) for y,row in enumerate(canvas) for x,(glyph,ink) in enumerate(row)
                            if glyph.strip()}
                for y,row in enumerate(canvas[:19]):
                    for x,(glyph,ink) in enumerate(row):
                        if ink not in ('bark','wood','woodlight','scar') or not glyph.strip():
                            continue
                        exposed = any(point not in occupied for point in
                                      ((x-1,y),(x+1,y),(x,y-1),(x,y+1)))
                        if exposed:
                            self.assertIn(glyph,'│─╱╲╭╮')
                        else:
                            interior_dots += glyph in '·◦'
        self.assertGreater(interior_dots,100)

    def test_outline_preserves_silhouette_and_foliage(self):
        canvas = [[(' ', '') for _ in range(7)] for _ in range(7)]
        for y in range(1,6):
            for x in range(1,6):
                canvas[y][x] = ('·','bark')
        canvas[1][3] = ('•','leaf1')
        before = {(x,y) for y,row in enumerate(canvas) for x,(g,ink) in enumerate(row) if g.strip()}
        bonsai.outline_exposed_wood(canvas)
        self.assertEqual(before, {(x,y) for y,row in enumerate(canvas) for x,(g,ink) in enumerate(row) if g.strip()})
        self.assertEqual(canvas[3][3],('·','bark'))
        self.assertEqual(canvas[1][3],('•','leaf1'))
        self.assertEqual(canvas[3][1],('│','wood'))
        self.assertEqual(canvas[1][2],('─','wood'))
        again = [row.copy() for row in canvas]
        bonsai.outline_exposed_wood(again)
        self.assertEqual(again,canvas)

    def test_top_sprays_fill_from_terminal_branches(self):
        for seed in range(24):
            leaves = [cell for cell in bonsai.specimen(seed, 30)
                      if cell[4].startswith('leaf') and cell[2] <= 31]
            upper = [cell for cell in leaves if cell[1] <= 6]
            self.assertGreaterEqual(len(upper), 25)
            graph = bonsai.branch_graph(seed)
            parents = {branch['parent'] for branch in graph}
            terminals = [branch['end'] for i, branch in enumerate(graph) if i not in parents]
            for x, y, *_ in leaves:
                self.assertTrue(any(abs(x-tx) <= 5 and abs(y-ty) <= 2.4
                                    for tx, ty in terminals))
            self.assertGreater(len(set((x, y) for x, y, *_ in upper)), 20)

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

    def test_buds_unfold_and_petioles_use_muted_terminal_leaf_color(self):
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
        # Petioles use the foliage slot at lower intensity.
        self.assertIn(bonsai.specimen_palette(42)['shoot_tip1'], image)
        self.assertIn(bonsai.specimen_palette(42)['leaf4'], image)


    def test_starting_wood_has_body_and_tapers(self):
        for seed in range(24):
            for day in (0, 3, 7):
                wood = bonsai.stem(day, seed)
                base = {x for x, y, *_ in wood if y == 18}
                self.assertGreaterEqual(len(base), 2)
                tip_y = min(cell[1] for cell in wood)
                self.assertEqual(sum(cell[1] == tip_y for cell in wood), 1)
            # Side branches remain visibly subordinate to the substantial trunk.
            graph = bonsai.branch_graph(seed)
            self.assertTrue(all(branch['width'] < 1.3 for branch in graph))

    def test_trunks_vary_without_disconnected_rows(self):
        silhouettes = set()
        bend_positions = set()
        for seed in range(120):
            path = bonsai.trunk_path(seed)
            self.assertEqual(path, bonsai.trunk_path(seed))
            self.assertEqual(path[0], 27)
            self.assertEqual(len(path), 15)
            self.assertTrue(all(abs(a - b) <= .951 for a, b in zip(path, path[1:])))
            silhouettes.add(tuple(round(x) for x in path))
            bend_positions.add(max(range(1, 14), key=lambda i: abs(path[i] - 27)))
        self.assertGreaterEqual(len(silhouettes), 35)
        self.assertEqual({bonsai.growth_pattern(seed)[0] for seed in range(120)},
                         {'upright', 'slant', 'bowed', 'forked', 'recurved', 'broom', 'old_oak', 'twisted_juniper'})
        self.assertGreater(len(bend_positions), 3)

    def test_cleanup_removes_detached_sticks_and_leaves(self):
        canvas = [[(' ', '') for _ in range(7)] for _ in range(7)]
        canvas[2][2] = ('╱', 'wood')
        canvas[1][2] = ('●', 'leaf1')
        canvas[2][3] = ('◆', 'leaf2')
        canvas[5][2] = ('│', 'wood')
        bonsai.cover_crown_wood(canvas)
        self.assertEqual(canvas[2][2], (' ', ''))
        self.assertEqual(canvas[5][2], ('│', 'wood'))
        self.assertEqual(sum(ink.startswith('leaf') for row in canvas for _, ink in row), 0)

    def test_starter_leaves_rise_then_extend_with_first_branches(self):
        for seed in range(24):
            def tips(day):
                return [(x, y) for x, y, _, _, ink in bonsai.juvenile_foliage(day, seed)
                        if ink.startswith('shoot_tip')]
            self.assertLess(tips(3)[0][1], tips(0)[0][1])
            left_start, right_start = tips(12)
            left_end, right_end = tips(22)
            for index, (start, end) in enumerate(zip((left_start, right_start), (left_end, right_end))):
                depth, _, _, _ = bonsai.branch_layout(seed)[index]
                origin = bonsai.trunk_path(seed)[depth]
                self.assertGreaterEqual(abs(end[0] - origin), abs(start[0] - origin))
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

    def test_background_greeting_uses_original_sprout_growth(self):
        from unittest.mock import patch
        with patch.object(bonsai, 'specimen_canvas', wraps=bonsai.specimen_canvas) as canvas, \
             patch.object(bonsai.time, 'monotonic', side_effect=[0, 0, .5, 1]), \
             patch.object(bonsai.time, 'sleep'), \
             patch.object(bonsai.shutil, 'get_terminal_size', return_value=os.terminal_size((80,40))), \
             patch.object(bonsai.os, 'write'), \
             patch('signal.signal'):
            bonsai.animate_background(42, ['#70bb50']*3, 1, 'informal')
        ages = [call.args[0] for call in canvas.call_args_list]
        self.assertEqual(ages, [0, 15, 30])
        sprout = bonsai.specimen_canvas(0,42)
        stalk = bonsai.specimen_canvas(7,42)
        mature = bonsai.specimen_canvas(30,42)
        def bounds(drawing):
            cells = [(x,y) for y,row in enumerate(drawing[:19])
                     for x,(glyph,ink) in enumerate(row) if glyph.strip()]
            return min(y for x,y in cells), max(x for x,y in cells)-min(x for x,y in cells)
        self.assertGreater(bounds(sprout)[0], bounds(stalk)[0])
        self.assertGreater(bounds(stalk)[0], bounds(mature)[0])
        self.assertLess(bounds(sprout)[1],bounds(mature)[1])
        self.assertTrue(any(ink.startswith('leaf') for row in sprout for glyph,ink in row))

    def test_animation_settles_without_a_last_frame_jump(self):
        samples = [bonsai.animation_day(i / 120, 1) for i in range(121)]
        self.assertEqual(samples[0], 0)
        self.assertEqual(samples[-1], 30)
        self.assertTrue(all(a <= b for a, b in zip(samples, samples[1:])))
        self.assertLess(samples[-1] - samples[-2], .01)
        for seed in range(16):
            almost = bonsai.render(bonsai.animation_day(.999, 1), seed, False, 80,
                                   fixed_height=True)
            final = bonsai.render(30, seed, False, 80, fixed_height=True)
            self.assertLessEqual(sum(a != b for a, b in zip(almost, final)), 2)
        self.assertEqual(bonsai.animation_day(2, 1), 30)
        self.assertEqual(bonsai.animation_day(-1, 1), 0)

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
                            frames_before_skip = output.count(b'\033[26A')
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
                    self.assertIn('╭──────────┴──────────╮'.encode(), plain)
                    self.assertGreaterEqual(output.count(b'\033[26A'), 2)
                    self.assertIn(b'\033[?25h', output)
                    self.assertNotIn(b'Traceback', output)
                    self.assertEqual(list(Path(directory).iterdir()), [])
                    if skip:
                        self.assertTrue(sent)
                        self.assertGreater(output.count(b'\033[26A') - frames_before_skip, 2)
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
                self.assertFalse(rows[0].strip())
                self.assertFalse(rows[-1].strip())
                self.assertNotIn('║', image)
                left = len(rows[0]) - 59
                self.assertLessEqual(abs(left - (columns - len(rows[0]))), 1)
                self.assertEqual(len({len(row) for row in rows}), 1)
                self.assertTrue(all(len(row) <= columns for row in rows))
                self.assertNotIn('\033', image)

    def test_seeded_wood_palette_has_variety_and_readable_shading(self):
        import re
        palettes = set()
        for seed in range(100):
            palette = bonsai.wood_palette(seed)
            self.assertEqual(palette, bonsai.wood_palette(seed))
            palettes.add(tuple(palette.values()))
            brightness = []
            for name in ('bark', 'scar', 'wood', 'woodlight'):
                rgb = list(map(int, re.findall(r'\d+', palette[name])[-3:]))
                self.assertTrue(all(0 <= value <= 255 for value in rgb))
                brightness.append(sum(rgb))
            self.assertEqual(brightness, sorted(brightness))
            self.assertIn(palette['wood'], bonsai.render(30, seed, True))
        self.assertGreater(len(palettes), 90)

    def test_wood_harmonizes_with_leaf_hue(self):
        import re
        def rgb(palette):
            return list(map(int, re.findall(r'\d+', palette['wood'])[-3:]))
        for seed in range(40):
            green = bonsai.wood_palette(seed, ['#70bb50'] * 3)
            blue = bonsai.wood_palette(seed, ['#6080dc'] * 3)
            rose = bonsai.wood_palette(seed, ['#db6095'] * 3)
            self.assertNotEqual(green, blue)
            self.assertNotEqual(green, rose)
            r, g, b = rgb(green)
            self.assertGreater(r, b)
            self.assertGreater(g, b)
            self.assertEqual(green, bonsai.wood_palette(seed, ['#70bb50'] * 3))
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rebos_shell/kitty.conf'
            path.parent.mkdir()
            path.write_text('color2 #40dd30\ncolor6 #ffffff\ncolor4 #6080dc\n')
            import json
            (path.parent / 'effective-palette.json').write_text(json.dumps(
                dict.fromkeys(('primary', 'secondary', 'tertiary'), '#6080dc')))
            with patch.dict(os.environ, {'XDG_CACHE_HOME': directory}):
                self.assertEqual(bonsai.terminal_leaf_palette(), ['#6080dc'] * 3)
                self.assertEqual(bonsai.wood_palette(42),
                                 bonsai.wood_palette(42, ['#6080dc'] * 3))
                self.assertIn(bonsai.wood_palette(42)['wood'], bonsai.render(30, 42))

    def test_green_leaves_get_brown_wood_and_red_leaves_get_red_wood(self):
        import colorsys
        import re
        for seed in range(100):
            for leaf, brown in (('#40bb30', True), ('#dd3030', False)):
                palette = bonsai.specimen_palette(seed, [leaf] * 3)
                for name in ('bark', 'wood', 'woodlight'):
                    rgb = map(int, re.findall(r'\d+', palette[name])[-3:])
                    hue, saturation, value = colorsys.rgb_to_hsv(*(v / 255 for v in rgb))
                    if brown:
                        self.assertGreater(hue, 0.04)
                        self.assertLess(hue, 0.1)
                    else:
                        self.assertLess(min(hue, 1 - hue), 0.03)
                    self.assertGreater(saturation, 0.2)
                    self.assertLessEqual(value, 0.48)
        mixed = ['#ee2222', '#bb9999', '#408040']
        self.assertEqual(bonsai.wood_palette(42, mixed),
                         bonsai.wood_palette(42, ['#ee2222'] * 3))

    def test_leaves_have_priority_over_all_supporting_colors(self):
        import colorsys
        import re
        for accent in ('#70bb50', '#6080dc', '#db6095', '#eeeeee', '#15121b'):
            palette = bonsai.specimen_palette(42, [accent] * 3)
            hsv = {}
            for name, ink in palette.items():
                if name:
                    rgb = map(int, re.findall(r'\d+', ink)[-3:])
                    hsv[name] = colorsys.rgb_to_hsv(*(value / 255 for value in rgb))
            leaves = [color for name, color in hsv.items() if name.startswith('leaf')]
            for name, (_, saturation, brightness) in hsv.items():
                if not name.startswith('leaf') and name not in ('pot_inlay', 'pot_shadow'):
                    self.assertLess(brightness, min(color[2] for color in leaves))
                    if accent not in ('#eeeeee',):
                        self.assertLess(saturation, min(color[1] for color in leaves))

    def test_two_wallpaper_accents_color_foliage_and_ceramics(self):
        import colorsys
        import re
        def hue(ink):
            rgb = [int(v) / 255 for v in re.findall(r'\d+', ink)[-3:]]
            return colorsys.rgb_to_hsv(*rgb)[0]
        blue_green = ['#57aae6', '#80d657', '#5790e6']
        palette = bonsai.specimen_palette(42, blue_green)
        # Blue and green mix through teal, without abrupt pure-color blocks.
        hues = [hue(palette[f'leaf{i}']) for i in (1, 7, 4)]
        self.assertGreater(hues[0], hues[1])
        self.assertGreater(hues[1], hues[2])
        self.assertTrue(all(.25 < h < .65 for h in hues))
        self.assertLess(max(abs(a-b) for a, b in zip(hues, hues[1:])), .15)
        for i in range(9):
            rgb = [int(v) / 255 for v in re.findall(r'\d+', palette[f'leaf{i}'])[-3:]]
            saturation = colorsys.rgb_to_hsv(*rgb)[1]
            self.assertGreater(saturation, .2)
            self.assertLessEqual(saturation, .72 + .01)
        self.assertEqual(palette['pot_inlay'], palette['leaf4'])
        # A later theme change must replace both colors, independent of tree seed.
        updated = bonsai.specimen_palette(42, ['#e65773', '#e6bb57', '#e65788'])
        self.assertNotEqual(palette['leaf4'], updated['leaf4'])
        self.assertNotEqual(palette['leaf1'], updated['leaf1'])

    def test_material_lighting_preserves_terminal_layout(self):
        import re
        palette = bonsai.specimen_palette(42)
        for day in (0, 10, 30):
            colored = bonsai.render(day, 42, True, 80)
            plain = bonsai.render(day, 42, False, 80)
            self.assertEqual(re.sub(r'\x1b\[[0-9;]*m', '', colored), plain)
            self.assertIn(palette['pot_rim'], colored)
            self.assertIn(palette['pot_foot'], colored)
            self.assertIn(palette['pot_pattern'], colored)

    def test_dark_wood_and_vibrant_pot_patterns(self):
        import colorsys
        import re
        for accent in ('#70bb50', '#6080dc', '#db6095', '#eeeeee'):
            for seed in range(30):
                palette = bonsai.specimen_palette(seed, [accent] * 3)
                self.assertEqual(palette['pot_inlay'], palette['leaf4'])
                self.assertEqual(palette['pot_shadow'], palette['leaf0'])
                for name in ('bark', 'wood', 'woodlight', 'scar'):
                    rgb = map(int, re.findall(r'\d+', palette[name])[-3:])
                    value = colorsys.rgb_to_hsv(*(channel / 255 for channel in rgb))[2]
                    self.assertLessEqual(value, 0.48)

    def test_trunk_color_variation_is_not_a_black_slit(self):
        import re
        def rgb(ink):
            return list(map(int, re.findall(r'\d+', ink)[-3:]))
        for seed in range(40):
            palette = bonsai.specimen_palette(seed, ['#50bb40'] * 3)
            bark, scar, wood = (rgb(palette[name]) for name in ('bark', 'scar', 'wood'))
            self.assertTrue(all(b <= s <= w for b, s, w in zip(bark, scar, wood)))
            self.assertNotEqual(bark, scar)
            image = bonsai.render(30, seed)
            self.assertTrue(any(bonsai.specimen_palette(seed)[name] in image
                                for name in ('wood_grain', 'bark_grain')))
            self.assertEqual(image, bonsai.render(30, seed))

    def test_wallpaper_primary_wins_over_semantic_green_and_other_accents(self):
        import json
        import re
        import colorsys
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / 'rebos_shell'
            cache.mkdir()
            (cache / 'effective-palette.json').write_text(json.dumps({
                'primary': '#e5bcc4', 'secondary': '#d6c1c4', 'tertiary': '#e5bfa7'}))
            (cache / 'kitty.conf').write_text('color2 #f0ffcc\ncolor6 #ffffff\ncolor4 #e5bcc4\n')
            with patch.dict(os.environ, {'XDG_CACHE_HOME': directory}):
                self.assertEqual(bonsai.terminal_leaf_palette()[0], '#e5bcc4')
                palette = bonsai.specimen_palette(42)
                rgb = map(int, re.findall(r'\d+', palette['leaf4'])[-3:])
                hue, _, _ = colorsys.rgb_to_hsv(*(channel / 255 for channel in rgb))
                self.assertLess(min(hue, 1 - hue), 0.05)
                self.assertEqual(palette['pot_inlay'], palette['leaf4'])

    def test_terminal_colors_follow_theme_without_rewriting_state(self):
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
                    self.assertIn(bonsai.wood_palette(seed)['wood'], image)
                    pot_inlay = bonsai.specimen_palette(seed)['pot_inlay']
                    self.assertIn(pot_inlay, image)
                    self.assertNotIn('\033[48;', image)
                    self.assertIn(bonsai.wood_palette(seed)['bark'], image)
                    self.assertEqual(state.read_text(), original)

    def test_branch_plans_vary_and_repeat_by_seed(self):
        layouts = set()
        for seed in range(48):
            layout = bonsai.branch_layout(seed)
            self.assertEqual(layout, bonsai.branch_layout(seed))
            layouts.add(tuple((depth, round(x), round(y)) for depth, x, y, born in layout))
            self.assertTrue(all(born >= (depth - 1) / .7 for depth, x, y, born in layout))
        self.assertGreater(len(layouts), 40)

    def test_branch_habits_keep_opposing_crown_support(self):
        for seed in range(80):
            trunk = bonsai.trunk_path(seed)
            shift = (trunk[-1]-27)*.6
            directions = {1 if x+shift >= trunk[depth] else -1
                          for depth,x,y,born in bonsai.branch_layout(seed)[:3]}
            self.assertEqual(directions, {-1,1})

    def test_branch_hierarchy_has_supported_unequal_tapered_forks(self):
        for seed in range(48):
            graph = bonsai.branch_graph(seed)
            descendants = {}
            for index, branch in enumerate(graph):
                parent = branch['parent']
                if parent is None:
                    continue
                self.assertLess(parent, index)
                source = graph[parent]
                self.assertEqual(branch['start'], bonsai.branch_point(source, branch['attachment']))
                arrival = source['born'] + source['length'] * branch['attachment'] * .55
                self.assertGreaterEqual(branch['born'], arrival)
                self.assertLess(branch['width'], source['width'])
                descendants.setdefault(parent, []).append(branch)
            self.assertTrue(descendants)
            for children in descendants.values():
                self.assertEqual(len(children), 2)
                self.assertNotEqual(children[0]['width'], children[1]['width'])
                self.assertNotEqual(children[0]['attachment'], children[1]['attachment'])

    def test_mature_limbs_keep_bends_large_enough_for_terminal_cells(self):
        checked = 0
        for seed in range(32):
            if bonsai.growth_pattern(seed)[0] == 'twisted_juniper':
                continue
            for branch in bonsai.branch_graph(seed):
                if branch['level'] or branch['length'] < 4:
                    continue
                start, end = branch['start'], branch['end']
                mid = bonsai.branch_point(branch, .5)
                straight_mid = (start[1] + end[1]) / 2
                # A sub-character offset was lost to rasterization in mature
                # frames. Major limbs must deviate by a whole terminal row.
                self.assertGreaterEqual(abs(mid[1] - straight_mid), 1.0)
                checked += 1
        self.assertGreater(checked, 24)
        # Completing growth must not substitute a different, straight skeleton.
        from unittest.mock import patch
        bonsai.branch_graph(42)
        for day in (22, 30, 90):
            with patch.object(bonsai, 'branch_point', wraps=bonsai.branch_point) as point:
                bonsai.natural_specimen(42, day)
            positions = {(id(call.args[0]), call.args[1]): call.args[0]['curve']
                         for call in point.call_args_list}
            if day == 22:
                early = positions
            else:
                self.assertEqual(positions, early)

    def test_terminal_character_is_distinct_stable_and_attached(self):
        bends = []
        for seed in range(12):
            graph = bonsai.branch_graph(seed)
            parents = {b['parent'] for b in graph if b['parent'] is not None}
            for index, branch in enumerate(graph):
                if index in parents:
                    self.assertNotIn('tip_bend', branch)
                    continue
                bends.append(branch['tip_bend'])
                self.assertEqual(bonsai.branch_point(branch, 0), branch['start'])
                for actual, expected in zip(bonsai.branch_point(branch, 1), branch['end']):
                    self.assertAlmostEqual(actual, expected)
            first = bonsai.natural_specimen(seed, 30)
            self.assertEqual(first, bonsai.natural_specimen(seed, 30))
            self.assertTrue(all(0 <= x < 57 and 0 <= y < 19
                                for x, y, born, glyph, ink in first if ink.startswith('leaf')))
        self.assertGreater(max(bends), .3)
        self.assertLess(min(bends), -.3)
        self.assertGreater(len(set(round(b, 2) for b in bends)), 12)

    def test_curve_strokes_follow_the_actual_branch_direction(self):
        # A tangent mismatch makes the final wood look jagged even when the
        # underlying path is smooth. Check the geometry independently.
        for seed in range(24):
            for branch in bonsai.branch_graph(seed):
                for t in (.001, .25, .5, .75, .999):
                    before = bonsai.branch_point(branch, t - 1e-5)
                    after = bonsai.branch_point(branch, t + 1e-5)
                    tangent = bonsai.branch_tangent(branch, t)
                    for axis in (0, 1):
                        self.assertAlmostEqual(
                            (after[axis] - before[axis]) / 2e-5,
                            tangent[axis], places=6)

    def test_terminal_bends_do_not_whip_back_at_the_tip(self):
        import math
        checked = 0
        for seed in range(48):
            for branch in bonsai.branch_graph(seed):
                if 'tip_bend' not in branch or branch['length'] < .5:
                    continue
                plain = dict(branch, tip_bend=0)
                ax, ay = bonsai.branch_tangent(plain, 1)
                bx, by = bonsai.branch_tangent(branch, 1)
                turn = abs(math.atan2(ax * by - ay * bx, ax * bx + ay * by))
                self.assertLess(turn, math.radians(25))
                checked += 1
        self.assertGreater(checked, 100)

    def test_continuing_forks_ease_out_of_the_parent_direction(self):
        checked = 0
        for seed in range(24):
            graph = bonsai.branch_graph(seed)
            for branch in graph:
                if 'departure' not in branch:
                    continue
                px, py = bonsai.branch_tangent(graph[branch['parent']], branch['attachment'])
                dx, dy = bonsai.branch_tangent(branch, 0)
                natural = dict(branch)
                del natural['departure']
                _, original = bonsai.branch_tangent(natural, 0)
                self.assertLess(abs(dy - py * dx / px), abs(original - py * dx / px))
                checked += 1
        self.assertGreater(checked, 100)

    def test_forked_type_replaces_narrow_one_direction_trees(self):
        checked = 0
        for seed in range(120):
            habit, side = bonsai.growth_pattern(seed)
            self.assertNotEqual(habit, 'windswept')
            if habit != 'forked':
                continue
            checked += 1
            trunk = bonsai.trunk_path(seed)
            shift = (trunk[-1]-27)*.6
            arms = bonsai.branch_layout(seed)[:2]
            directions = [1 if x+shift > trunk[depth] else -1 for depth,x,y,born in arms]
            self.assertEqual(set(directions), {-1, 1})
            self.assertGreater(abs(arms[0][1]-arms[1][1]), 14)
            leaves = [cell for cell in bonsai.specimen(seed,30)
                      if cell[4].startswith('leaf') and cell[2] <= 31]
            self.assertGreater(max(cell[0] for cell in leaves)-min(cell[0] for cell in leaves), 18)
        self.assertGreater(checked, 10)

    def test_directional_trunks_do_not_jitter_backwards(self):
        checked = 0
        for seed in range(200):
            habit, side = bonsai.growth_pattern(seed)
            if habit != 'slant':
                continue
            checked += 1
            path = bonsai.trunk_path(seed)
            self.assertTrue(all((b-a)*side >= 0 for a,b in zip(path,path[1:])))
        self.assertGreater(checked, 20)

    def test_trunk_grain_tracks_its_local_bend(self):
        for seed in range(48):
            path = bonsai.trunk_path(seed)
            for x,y,born,glyph,ink in bonsai.stem(30,seed):
                if ink != 'bark' or glyph not in '╱╲╎':
                    continue
                depth = 18-y
                turn = path[min(depth+1,14)]-path[depth]
                expected = '╱' if turn > .2 else '╲' if turn < -.2 else '╎'
                self.assertEqual(glyph, expected)

    def test_final_silhouette_is_connected_throughout_growth(self):
        for seed in range(64):
            for day in (0, 3, 7, 14, 22, 30):
                rows = bonsai.render(day, seed, False, 59, ['#85b470']*3,
                                    fixed_height=True).splitlines()[1:20]
                points = {(x,y) for y,row in enumerate(rows)
                          for x,char in enumerate(row[1:-1]) if char != ' '}
                reached = {(x,y) for x,y in points if y == 18}
                pending = list(reached)
                while pending:
                    x,y = pending.pop()
                    for dx in (-1,0,1):
                        for dy in (-1,0,1):
                            point = (x+dx,y+dy)
                            if point in points and point not in reached:
                                reached.add(point)
                                pending.append(point)
                self.assertEqual(points, reached, (seed, day))
                if day == 30:
                    self.assertGreater(sum(char in '♣●◆•·' for row in rows for char in row), 30)

    def test_shallow_main_branches_cannot_form_long_shelves(self):
        for seed in range(80):
            for branch in bonsai.branch_graph(seed):
                if branch['parent'] is not None or branch['leader'] or branch.get('lower'):
                    continue
                x,y = branch['start']
                tx,ty = branch['end']
                self.assertLessEqual(abs(tx-x), 1.5+3*max(0,y-ty)+1e-8)

    def test_main_branch_keeps_a_tapered_body_beyond_its_base(self):
        from unittest.mock import patch
        import math
        branch = dict(start=(15,14), end=(29,8), length=math.hypot(14,6),
                      born=0, width=1.2, level=0, curve=.4, parent=None, leader=False)
        with patch.object(bonsai, 'branch_graph', return_value=[branch]):
            wood = {(x,y):ink for x,y,born,glyph,ink in bonsai.natural_specimen(42,30)
                    if not ink.startswith('leaf')}
        middle = [(x,y) for x,y in wood if 21 <= x <= 24]
        self.assertGreaterEqual(sum(wood[point] == 'bark' for point in middle), 3)
        self.assertTrue(all(2 <= sum(xx == x for xx,y in wood) <= 3 for x in range(21,25)))
        self.assertTrue(all(sum(xx == x for xx,y in wood) == 1 for x in range(26,30)))
        self.assertLessEqual(max(sum(xx == x for xx,y in wood) for x in range(15,30)), 3)

    def test_shading_is_spaced_without_removing_branch_body(self):
        for seed in range(16):
            canvas = [[('▒', 'bark') for _ in range(9)] for _ in range(9)]
            bonsai.space_bark_shading(canvas, seed)
            shaded = {(x,y) for y,row in enumerate(canvas)
                      for x,(glyph,ink) in enumerate(row) if glyph in '░▒▓'}
            self.assertTrue(shaded)
            self.assertLessEqual(len(shaded), 23)
            self.assertTrue(all(glyph.strip() for row in canvas for glyph,ink in row))
            for x,y in shaded:
                self.assertFalse(any((x+dx,y+dy) in shaded
                                     for dx in (-1,0,1) for dy in (-1,0,1) if dx or dy))
            again = [row.copy() for row in canvas]
            bonsai.space_bark_shading(again, seed)
            self.assertEqual(again, canvas)

    def test_lower_shoots_removed_and_blossoms_are_occasional(self):
        blooming = plain = 0
        for seed in range(64):
            self.assertFalse(any(branch.get('lower') for branch in bonsai.branch_graph(seed)))
            sites = bonsai.blossom_sites(seed)
            self.assertEqual(sites, bonsai.blossom_sites(seed))
            if sites:
                blooming += 1
                self.assertTrue(2 <= len(sites) <= 4)
                for x,y,born in sites:
                    self.assertTrue(21 <= born <= 26)
                for i,(x,y,born) in enumerate(sites):
                    self.assertTrue(all(max(abs(x-px),abs(y-py)) >= 3 for px,py,_ in sites[i+1:]))
            else:
                plain += 1
        self.assertGreater(blooming, 10)
        self.assertGreater(plain, 20)

    def test_blossoms_only_replace_existing_foliage_late_in_growth(self):
        for seed in range(48):
            canvas = [[(' ', '') for _ in range(57)] for _ in range(24)]
            for x,y,born in bonsai.blossom_sites(seed):
                canvas[y][x] = ('●','leaf1')
            early = [row.copy() for row in canvas]
            bonsai.add_blossoms(early,seed,10)
            self.assertEqual(early,canvas)
            occupied = {(x,y) for y,row in enumerate(canvas) for x,(glyph,ink) in enumerate(row) if glyph != ' '}
            bonsai.add_blossoms(canvas,seed,30)
            self.assertEqual(occupied, {(x,y) for y,row in enumerate(canvas) for x,(glyph,ink) in enumerate(row) if glyph != ' '})
            for x,y,born in bonsai.blossom_sites(seed):
                self.assertEqual(canvas[y][x], ('✿','blossom'))
            blank = [[(' ', '') for _ in range(57)] for _ in range(24)]
            bonsai.add_blossoms(blank,seed,30)
            self.assertTrue(all(glyph == ' ' for row in blank for glyph,ink in row))

    def test_actual_blossom_rendering_keeps_early_growth_clean(self):
        flowering = 0
        for seed in range(48):
            early = bonsai.render(10,seed,False,80,['#85b470']*3)
            self.assertNotIn('✿',early)
            mature = bonsai.render(30,seed,False,80,['#85b470']*3)
            count = mature.count('✿')
            self.assertLessEqual(count,4)
            flowering += count > 0
        self.assertGreater(flowering,10)
        self.assertLess(flowering,35)

    def test_occasional_knurling_is_stable_sparse_and_only_on_bark(self):
        textured = plain = 0
        for seed in range(64):
            sites = bonsai.knurl_sites(seed)
            self.assertEqual(sites,bonsai.knurl_sites(seed))
            self.assertLessEqual(len(sites),2)
            textured += bool(sites)
            plain += not sites
            canvas = [[(' ', '') for _ in range(57)] for _ in range(24)]
            for x,y,born in sites:
                canvas[y][x] = ('░','bark')
                canvas[y+1][x] = ('·','bark')
            early = [row.copy() for row in canvas]
            bonsai.add_knurling(early,seed,10)
            self.assertEqual(early,canvas)
            occupied = {(x,y) for y,row in enumerate(canvas) for x,(g,ink) in enumerate(row) if g != ' '}
            bonsai.add_knurling(canvas,seed,30)
            self.assertEqual(occupied,{(x,y) for y,row in enumerate(canvas) for x,(g,ink) in enumerate(row) if g != ' '})
            for x,y,born in sites:
                self.assertEqual(canvas[y][x],('◦','woodlight'))
                self.assertEqual(canvas[y+1][x],('╎','bark'))
            blank = [[('●','leaf1') for _ in range(57)] for _ in range(24)]
            bonsai.add_knurling(blank,seed,30)
            self.assertTrue(all(cell == ('●','leaf1') for row in blank for cell in row))
        self.assertGreater(textured,10)
        self.assertGreater(plain,20)

    def test_knurling_appears_in_some_mature_renderings_only(self):
        knotted = 0
        for seed in range(48):
            self.assertNotIn('◦',bonsai.render(10,seed,False,80,['#85b470']*3))
            count = bonsai.render(30,seed,False,80,['#85b470']*3).count('◦')
            self.assertLessEqual(count,2)
            knotted += count > 0
        self.assertGreater(knotted,5)
        self.assertLess(knotted,35)

    def test_occasional_scar_stays_inside_middle_trunk_and_grows_continuously(self):
        scarred = plain = 0
        for seed in range(64):
            scar = bonsai.trunk_scar(seed)
            self.assertEqual(scar,bonsai.trunk_scar(seed))
            scarred += bool(scar)
            plain += not scar
            if not scar:
                continue
            self.assertTrue(3 <= len(scar) <= 6)
            bark = {(x,y) for x,y,born,glyph,ink in bonsai.stem(30,seed) if ink == 'bark'}
            self.assertTrue(all((x,y) in bark and 9 <= y <= 16 for x,y,glyph,born in scar))
            for a,b in zip(scar,scar[1:]):
                self.assertLessEqual(abs(a[0]-b[0]),1)
                self.assertEqual(a[1]-b[1],1)
                self.assertGreater(b[3],a[3])
            canvas = [[(' ', '') for _ in range(57)] for _ in range(24)]
            for x,y in bark:
                canvas[y][x] = ('░','bark')
            early = [row.copy() for row in canvas]
            bonsai.add_trunk_scar(early,seed,10)
            self.assertEqual(canvas,early)
            bonsai.add_trunk_scar(canvas,seed,30)
            self.assertEqual({(x,y) for y,row in enumerate(canvas) for x,(g,ink) in enumerate(row) if g != ' '},bark)
            for x,y,glyph,born in scar:
                self.assertEqual(canvas[y][x],(glyph,'scar'))
            foliage = [[('●','leaf1') for _ in range(57)] for _ in range(24)]
            bonsai.add_trunk_scar(foliage,seed,30)
            self.assertTrue(all(cell == ('●','leaf1') for row in foliage for cell in row))
        self.assertGreater(scarred,10)
        self.assertGreater(plain,20)

    def test_rounded_crown_forms_have_lower_structure_and_no_flat_outer_roof(self):
        checked = set()
        for seed in range(80):
            habit, side = bonsai.growth_pattern(seed)
            if habit not in ('forked','bowed','upright','recurved'):
                continue
            checked.add(habit)
            center = bonsai.trunk_path(seed)[-1]
            for branch in bonsai.branch_graph(seed):
                x,y = branch['end']
                self.assertGreaterEqual(y+1e-8,2.8+(abs(x-center)/6)**1.4)
            layout = bonsai.branch_layout(seed)
            if habit == 'forked':
                self.assertTrue(all(depth <= 7 for depth,x,y,born in layout[:2]))
                self.assertGreater(layout[1][2]-layout[0][2], .3)
            if habit == 'upright':
                self.assertLessEqual(layout[0][0],6)
            self.assertFalse(any(glyph in '╭╮' and ink == 'woodlight'
                                 for x,y,born,glyph,ink in bonsai.stem(30,seed)))
        self.assertEqual(checked,{'forked','bowed','upright','recurved'})

    def test_recurved_form_has_a_gentle_return_and_restrained_primary_reach(self):
        checked = 0
        for seed in range(120):
            if bonsai.growth_pattern(seed)[0] != 'recurved':
                continue
            checked += 1
            path = bonsai.trunk_path(seed)
            self.assertLess(max(abs(x-27) for x in path),5.1)
            self.assertLess(abs(path[-1]-27),1.8)
            self.assertTrue(all(abs(c-2*b+a) < .4 for a,b,c in zip(path,path[1:],path[2:])))
            self.assertLessEqual(bonsai.branch_layout(seed)[0][0],6)
            shift = (path[-1]-27)*.6
            for depth,x,y,born in bonsai.branch_layout(seed)[:3]:
                self.assertLessEqual(abs(x+shift-path[depth]),9)
        self.assertGreater(checked,10)

    def test_broom_is_retained_and_twin_leader_removed(self):
        broom_count = 0
        for seed in range(120):
            habit, side = bonsai.growth_pattern(seed)
            self.assertNotEqual(habit,'twin_leader')
            if habit != 'broom':
                continue
            broom_count += 1
            roots = [branch for branch in bonsai.branch_graph(seed) if branch['parent'] is None]
            self.assertEqual(len(roots),3)
            self.assertEqual(min(cell[1] for cell in bonsai.stem(30,seed)),12)
            self.assertTrue(all(branch['start'][1] >= 12 for branch in roots))
        self.assertGreater(broom_count,10)
        for seed in (9,19):
            self.assertNotEqual(bonsai.growth_pattern(seed)[0],'twin_leader')

    def test_slant_form_keeps_its_crown_close_and_balanced(self):
        checked = 0
        for seed in range(160):
            habit,side = bonsai.growth_pattern(seed)
            if habit != 'slant':
                continue
            checked += 1
            trunk = bonsai.trunk_path(seed)
            self.assertLessEqual(abs(trunk[-1]-27),5.5)
            shift = (trunk[-1]-27)*.6
            layout = bonsai.branch_layout(seed)
            depth,x,y,born = layout[0]
            self.assertLessEqual(depth,6)
            self.assertLess((x+shift-trunk[depth])*side,0)
            for depth,x,y,born in layout[:3]:
                self.assertLessEqual(abs(x+shift-trunk[depth]),8)
            for branch in bonsai.branch_graph(seed):
                x,y = branch['end']
                self.assertGreaterEqual(y+1e-8,2.8+(abs(x-trunk[-1])/6)**1.4)
        self.assertGreater(checked,15)

    def test_old_oak_has_a_short_stout_base_and_unequal_main_limbs(self):
        checked = 0
        for seed in range(160):
            if bonsai.growth_pattern(seed)[0] != 'old_oak':
                continue
            checked += 1
            wood = bonsai.stem(30,seed)
            self.assertEqual(min(cell[1] for cell in wood),11)
            roots = [branch for branch in bonsai.branch_graph(seed) if branch['parent'] is None]
            self.assertEqual(len(roots),3)
            self.assertEqual([branch['width'] for branch in roots],[1.25,1.1,.9])
            self.assertTrue(all(branch['start'][1] >= 11 for branch in roots))
        self.assertGreater(checked,10)

    def test_twisted_juniper_has_three_or_four_supported_pad_groups(self):
        checked = 0
        for seed in range(160):
            if bonsai.growth_pattern(seed)[0] != 'twisted_juniper':
                continue
            checked += 1
            path = bonsai.trunk_path(seed)
            self.assertGreater(max(path)-min(path),3.5)
            graph = bonsai.branch_graph(seed)
            parents = {branch['parent'] for branch in graph if branch['parent'] is not None}
            pads = [branch for i,branch in enumerate(graph) if i not in parents
                    and (branch['parent'] is None or branch.get('pad_tip'))]
            roots = [branch for branch in graph if branch['parent'] is None]
            self.assertIn(len(pads),(3,4))
            self.assertEqual(len(pads),len(roots))
            self.assertLessEqual(max(branch['level'] for branch in graph),1)
        self.assertGreater(checked,10)

    def test_every_form_is_seated_in_the_soil_and_pot_rim(self):
        seen = set()
        for seed in range(80):
            seen.add(bonsai.growth_pattern(seed)[0])
            for day in (0,7,14,30):
                rows = bonsai.render(day,seed,False,59,['#85b470']*3,
                                    fixed_height=True).splitlines()[1:-1]
                body = [row[1:-1] for row in rows]
                self.assertEqual(body[18][27],'│')
                self.assertEqual(body[19][27],'┴')
                self.assertEqual((body[18][17],body[18][37]),(' ',' '))
                self.assertTrue(all(char == ' ' for char in body[18][18:22]+body[18][33:37]))
                self.assertEqual((body[19][16],body[19][38]),('╭','╮'))
        self.assertTrue({'old_oak','twisted_juniper','broom','forked'} <= seen)

    def test_new_launches_use_fresh_seeds_and_explicit_seed_is_repeatable(self):
        from unittest.mock import patch, Mock
        with patch('sys.stdout', Mock(isatty=lambda: True, fileno=lambda: 1)), \
             patch('sys.stdin', Mock(isatty=lambda: True, fileno=lambda: 0)), \
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
            self.assertIn('╭──────────┴──────────╮', result.stdout)
            self.assertNotIn('\033', result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_redirected_greeting_is_quiet(self):
        result = subprocess.run([str(SOURCE)], capture_output=True, check=True)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(result.stderr, b'')


if __name__ == '__main__':
    unittest.main()
