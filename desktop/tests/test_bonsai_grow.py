"""Regression checks for the restored standalone S-shaped bonsai."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / 'system/bin/bonsai-grow'
loader = importlib.machinery.SourceFileLoader('bonsai_grow', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
bonsai = importlib.util.module_from_spec(spec)
loader.exec_module(bonsai)


class BonsaiGrowTests(unittest.TestCase):
    def test_theme_background_tracks_export_and_rejects_invalid_colors(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / 'rebos_shell'
            cache.mkdir()
            path = cache / 'effective-palette.json'
            with patch.dict(os.environ, {'XDG_CACHE_HOME': directory}):
                for value, expected in (('#123456', (16, 46, 76)),
                                        ('#e0dCd8', (197, 194, 190)),
                                        ('bad', (15, 15, 15)), (None, (15, 15, 15))):
                    path.write_text(json.dumps({'background': value}))
                    self.assertEqual(bonsai.theme_background(), expected)
                    image = bonsai.render(30, 42, True, 80)
                    self.assertIn('\033[48;2;{};{};{}m'.format(*expected), image)
                path.write_text('broken')
                self.assertEqual(bonsai.theme_background(), (15, 15, 15))
                path.unlink()
                self.assertEqual(bonsai.theme_background(), (15, 15, 15))

    def test_kitty_backing_follows_theme_opacity_with_crisp_rim(self):
        import json
        import struct
        import zlib
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / 'rebos_shell'
            cache.mkdir()
            with patch.dict(os.environ, {'XDG_CACHE_HOME': directory, 'TERM': 'xterm-kitty'}), \
                 patch.object(bonsai.sys.stdout, 'isatty', return_value=True), \
                 patch.object(bonsai.sys.stdout, 'fileno', return_value=1), \
                 patch.object(bonsai.fcntl, 'ioctl', return_value=struct.pack('HHHH', 40, 80, 800, 800)):
                for opacity in (0, 0.48, 1):
                    (cache / 'effective-palette.json').write_text(json.dumps(
                        {'background': '#123456', 'opacity': opacity}))
                    with patch.object(bonsai, 'rounded_frame_png', wraps=bonsai.rounded_frame_png) as render_png:
                        bonsai.kitty_frame(26, 59, [240, 130, 80])
                        args = render_png.call_args.args
                    self.assertEqual(args[-2], (16, 46, 76))
                    self.assertAlmostEqual(args[-1], opacity)
                    png = bonsai.rounded_frame_png(*args)
                    offset, compressed = 8, b''
                    while offset < len(png):
                        size = struct.unpack('!I', png[offset:offset + 4])[0]
                        if png[offset + 4:offset + 8] == b'IDAT':
                            compressed += png[offset + 8:offset + 8 + size]
                        offset += size + 12
                    pixels = zlib.decompress(compressed)
                    def pixel(x, y):
                        start = y * (590 * 4 + 1) + 1 + x * 4
                        return tuple(pixels[start:start + 4])
                    self.assertEqual(pixel(295, 260), (16, 46, 76, round(255 * opacity)))
                    self.assertEqual(pixel(295, 10), (240, 130, 80, 255))
                    self.assertEqual(pixel(295, 0)[3], 0)
                    self.assertEqual(pixel(295, 495)[3], 255, "base stays solid")
                    self.assertEqual(pixel(230, 485)[3], 255, "solid foot stays opaque")
                    self.assertEqual(pixel(210, 481)[3], round(255 * opacity),
                                     "open space beside feet retains theme opacity")
                    self.assertGreater(sum(pixel(295, 497)[:3]), sum(pixel(295, 500)[:3]), "bevel shades into the lower lip")
                    self.assertEqual(pixel(295, 510)[3], 255, "deeper base stays opaque")
                    self.assertEqual(pixel(295, 519)[3], 0, "clearance below the base")

    def test_transparent_materials_gain_definition_without_changing_accents(self):
        import json
        import re
        from unittest.mock import patch
        theme = ['#85b470', '#b8ce93', '#67bca3']
        def brightness(ink):
            return sum(map(int, re.findall(r'\d+', ink)[-3:]))
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / 'rebos_shell'
            cache.mkdir()
            path = cache / 'effective-palette.json'
            with patch.dict(os.environ, {'XDG_CACHE_HOME': directory}):
                path.write_text(json.dumps({'opacity': 1}))
                opaque = bonsai.specimen_palette(42, theme)
                path.write_text(json.dumps({'opacity': 0.48}))
                glass = bonsai.specimen_palette(42, theme)
                for role in ('bark', 'wood', 'woodlight', 'ceramic_body_11', 'ceramic_foot_11'):
                    self.assertGreater(brightness(glass[role]), brightness(opaque[role]))
                for role in ('leaf4', 'ceramic_inlay_main', 'ceramic_inlay_accent'):
                    self.assertEqual(glass[role], opaque[role])
                for invalid in (None, '0.5', True, float('nan')):
                    path.write_text(json.dumps({'opacity': invalid}))
                    self.assertEqual(bonsai.transparency_lift(), 0)
                path.write_text('invalid')
                self.assertEqual(bonsai.transparency_lift(), 0)

    def test_standalone_specimen(self):
        palette = ['#85b470', '#b8ce93', '#67bca3']
        image = bonsai.render(30, 42, False, 80, palette)
        self.assertEqual(image, bonsai.render(30, 42, False, 80, palette))
        self.assertIn('╭══════════┴══════════╮', image)
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

    def test_sprays_fill_from_supported_tips_and_inner_shoots(self):
        for seed in range(24):
            leaves = [cell for cell in bonsai.specimen(seed, 30)
                      if cell[4].startswith('leaf') and cell[2] <= 31]
            upper = [cell for cell in leaves if cell[1] <= 6]
            self.assertGreaterEqual(len(upper), 25)
            supports = [spray['end'] for spray in bonsai.foliage_sprays(seed)]
            for x, y, *_ in leaves:
                self.assertTrue(any(abs(x-tx) <= 5 and abs(y-ty) <= 2.4
                                    for tx, ty in supports))
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
            self.assertTrue(shoots)
            self.assertTrue(all(cell[3] in '╱╲─' for cell in shoots))
        self.assertEqual(glyphs, ['·', '•', '●'])
        image = bonsai.render(0, 42, True, 80, ['#00ff00'] * 3)
        # Petioles use the foliage slot at lower intensity.
        self.assertIn(bonsai.specimen_palette(42)['shoot_tip1'], image)
        self.assertIn(bonsai.specimen_palette(42)['leaf4'], image)


    def test_growing_branches_have_leaves_at_the_current_tip(self):
        import math
        checked = 0
        for seed in range(48):
            for day in (7, 10, 12, 14, 16, 18, 22, 26, 30):
                plan = bonsai.natural_specimen(seed, day)
                leaves = {(x,y) for x,y,born,glyph,ink in plan if ink.startswith('leaf')}
                canvas = bonsai.specimen_canvas(day, seed)
                for branch in bonsai.branch_graph(seed):
                    arrival = branch['born'] + branch['length'] * .55
                    if day+1 >= arrival+.5 or day+1 < branch['born']:
                        continue
                    steps = max(1,math.ceil(branch['length']*2))
                    t = min(1,(day+1-branch['born'])/max(.001,branch['length']*.55))
                    step = min(steps,math.floor(t*steps+1e-9))
                    if not step:
                        continue
                    x,y = map(round,bonsai.branch_point(branch,step/steps))
                    self.assertIn((x,y), leaves, (seed,day))
                    # Verify the composited frame too: stem painting and
                    # connectivity cleanup must not erase the living tip.
                    self.assertTrue(canvas[y][x][1].startswith('leaf'), (seed,day,x,y))
                    checked += 1
        self.assertGreater(checked,1000)

    def test_opening_is_a_tiny_sprout_before_it_develops_bark(self):
        for seed in range(48):
            canvas = bonsai.specimen_canvas(0, seed)
            points = [(x,y,ink) for y,row in enumerate(canvas[:19])
                      for x,(glyph,ink) in enumerate(row) if glyph.strip()]
            self.assertEqual(len(points), 4)
            self.assertEqual(max(x for x,y,ink in points)-min(x for x,y,ink in points), 2)
            self.assertEqual(min(y for x,y,ink in points), 17)
            self.assertFalse(any(ink == 'bark' for x,y,ink in points))
            self.assertEqual(sum(ink.startswith('leaf') for x,y,ink in points), 2)

    def test_outer_twigs_are_subordinate_and_do_not_extend_into_long_spurs(self):
        checked = 0
        for seed in range(64):
            graph = bonsai.branch_graph(seed)
            for twig in graph:
                if twig['level'] != 1 or twig['attachment'] < .6:
                    continue
                parent = graph[twig['parent']]
                self.assertLessEqual(twig['width'], parent['width'] * .28)
                self.assertLessEqual(abs(twig['end'][0]-parent['end'][0]), .91)
                self.assertLess(twig['end'][1], twig['start'][1])
                checked += 1
        self.assertGreater(checked, 200)

    def test_starting_wood_has_body_and_tapers(self):
        for seed in range(24):
            for day in (0, 3, 7):
                wood = bonsai.stem(day, seed)
                base = {x for x, y, *_ in wood if y == 18}
                if day == 0:
                    self.assertEqual(len(base), 1)
                else:
                    self.assertGreaterEqual(len(base), 1 if day == 3 else 2)
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

    def test_all_pot_patterns_and_accents_are_mirrored(self):
        from unittest.mock import patch
        mirror = str.maketrans('╭╮╰╯┌┐└┘╱╲╴╶', '╮╭╯╰┐┌┘└╲╱╶╴')
        for motif in bonsai.POT_MOTIFS:
            with self.subTest(motif=motif), patch.object(bonsai.random.Random, 'choice', return_value=motif):
                for row in bonsai.pot_rows(0):
                    self.assertEqual(row, row[::-1].translate(mirror))
                    accents = [char in bonsai.POT_ACCENT_MARKS for char in row]
                    self.assertEqual(accents, accents[::-1])

    def test_aged_trunk_hollow_preserves_silhouette_and_existing_details(self):
        visible = 0
        from unittest.mock import patch
        for seed in range(40):
            self.assertEqual(bonsai.trunk_hollow(seed), bonsai.trunk_hollow(seed))
            with patch.object(bonsai, 'add_trunk_hollow'):
                before = bonsai.specimen_canvas(30, seed)
            after = bonsai.specimen_canvas(30, seed)
            changed = [(x, y) for y, row in enumerate(after) for x, cell in enumerate(row)
                       if cell != before[y][x]]
            visible += bool(changed)
            for x, y in changed:
                self.assertEqual(before[y][x][1], 'bark')
                self.assertTrue(10 <= y <= 18)
                self.assertEqual(after[y][x][1], 'woodlight')
            early = [row[:] for row in before]
            bonsai.add_trunk_hollow(early, seed, 20)
            self.assertEqual(early, before)
        self.assertGreater(visible, 5)
        self.assertLess(visible, 35)

    def test_hollow_chance_is_fixed_per_tree_and_balanced(self):
        chosen = 0
        for seed in range(200):
            sites = bonsai.trunk_hollow(seed)
            bonsai.trunk_hollow.cache_clear()
            self.assertEqual(sites, bonsai.trunk_hollow(seed))
            chosen += bool(sites)
        self.assertTrue(75 <= chosen <= 125, chosen)

    def test_background_greeting_uses_original_sprout_growth(self):
        from unittest.mock import patch
        with patch.object(bonsai, 'specimen_canvas', wraps=bonsai.specimen_canvas) as canvas, \
             patch.object(bonsai.time, 'monotonic', side_effect=[0, 0, .5, 1]), \
             patch.object(bonsai.time, 'sleep'), \
             patch.object(bonsai.shutil, 'get_terminal_size', side_effect=[os.terminal_size((80,40))]*4 + [os.terminal_size((81,40))]), \
             patch.object(bonsai.os, 'write'), \
             patch.object(bonsai, 'start_refill'), \
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

    def test_render_keeps_glass_without_sky_decorations(self):
        with patch.object(bonsai, 'sky_pane', side_effect=AssertionError('sky drawn')), \
             patch.object(bonsai, 'place_glass_marks', wraps=bonsai.place_glass_marks) as glass:
            for day in (0, 15, 30):
                frames = [bonsai.render(day, 42, hour=hour) for hour in (0, 6, 12, 18)]
                self.assertTrue(all(frame == frames[0] for frame in frames))
            self.assertEqual(glass.call_count, 12)
            self.assertTrue(any(ink == 'glass' for row in glass.call_args.args[0]
                                for glyph, ink in row))

    def test_idle_glass_scene_stays_stable_after_growth(self):
        size = os.terminal_size((80, 40))
        local = __import__('time')
        morning = local.struct_time((2026, 11, 15, 8, 0, 0, 6, 319, -1))
        afternoon = local.struct_time((2026, 11, 15, 16, 0, 0, 6, 319, -1))
        with patch.object(bonsai.time, 'monotonic', side_effect=[0, 2, 32]), \
             patch.object(bonsai.time, 'localtime', side_effect=[morning, afternoon]), \
             patch.object(bonsai.time, 'sleep') as sleep, \
             patch.object(bonsai.shutil, 'get_terminal_size', side_effect=[size]*3 + [os.terminal_size((81, 40))]), \
             patch.object(bonsai.os, 'write') as write, \
             patch.object(bonsai, 'start_refill'), patch('signal.signal'):
            bonsai.animate_background(42, ['#70bb50']*3, 1, 'informal')
        self.assertEqual(write.call_count, 2)
        self.assertEqual(write.call_args_list[0].args[1], write.call_args_list[1].args[1])
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [30, 30])
        for hours in ((7, 12, 17), (19, 0, 5)):
            positions = []
            for hour in hours:
                canvas = [[(' ', '') for _ in range(57)] for _ in range(24)]
                bonsai.sky_pane(canvas, hour)
                body = [(x, y) for y, row in enumerate(canvas)
                        for x, (_, ink) in enumerate(row) if ink.startswith('sky_orb')]
                positions.append((sum(x for x, y in body) / len(body),
                                  sum(y for x, y in body) / len(body)))
            self.assertLess(positions[0][0], positions[1][0])
            self.assertEqual(positions[1], positions[2])
            self.assertEqual(positions[1][1], positions[0][1])

    def test_large_sun_and_moon_stay_inside_the_glass(self):
        for hour in range(24):
            canvas = [[(' ', '') for _ in range(57)] for _ in range(24)]
            bonsai.sky_pane(canvas, hour)
            body = [(x, y) for y, row in enumerate(canvas)
                    for x, (_, ink) in enumerate(row) if ink.startswith('sky_orb')]
            self.assertGreaterEqual(len(body), 20)
            self.assertGreaterEqual(max(x for x, y in body) - min(x for x, y in body), 5)
            self.assertEqual(max(y for x, y in body) - min(y for x, y in body),
                             6)

    def test_sky_leaves_a_dark_contour_and_lights_the_foreground(self):
        canvas = [[(' ', '') for _ in range(57)] for _ in range(24)]
        # A thin branch crossing the afternoon corner sun.
        for y in range(2, 7):
            canvas[y][48] = ('│', 'wood')
        before = [row[:] for row in canvas]
        lit = bonsai.sky_pane(canvas, 12)
        self.assertTrue(lit)
        self.assertTrue(any(ink.startswith('sky_orb') for row in canvas for _, ink in row))
        for y in range(2, 7):
            self.assertEqual(canvas[y][48], before[y][48])
            for x in (47, 49):
                self.assertFalse(canvas[y][x][1].startswith('sky_orb'))
        original = '\033[0;38;2;70;90;60m'
        day = bonsai.backlit_ink(original, True)
        night = bonsai.backlit_ink(original, False)
        self.assertNotEqual(day, night)
        self.assertNotEqual(day, original)
        # Integration: texture and all original glyphs survive real overlap.
        import re
        base = bonsai.specimen_canvas(30, 42)
        image = bonsai.render(30, 42, True, 59, fixed_height=True, hour=12)
        rows = re.sub(r'\x1b\[[0-9;]*m', '', image).splitlines()
        for y, row in enumerate(base):
            for x, (glyph, ink) in enumerate(row):
                if ink:
                    self.assertEqual(rows[y + 1][x + 1], glyph)

    def test_sun_has_radial_light_and_time_dependent_warmth(self):
        import re
        def rgb(ink):
            return tuple(map(int, re.findall(r'\d+', ink)[-3:]))
        noon = bonsai.sun_palette(12)
        dawn = bonsai.sun_palette(6)
        dusk = bonsai.sun_palette(18)
        self.assertEqual(dawn, dusk)
        self.assertNotEqual(noon, dawn)
        shades = [rgb(noon[f'sky_orb_sun{i}']) for i in range(8)]
        self.assertEqual(len(set(shades)), 8)
        self.assertTrue(all(sum(a) > sum(b) for a, b in zip(shades, shades[1:])))
        self.assertGreater(rgb(noon['sky_orb_sun0'])[2], rgb(dawn['sky_orb_sun0'])[2])
        for hour in (6, 12, 17):
            canvas = [[(' ', '') for _ in range(57)] for _ in range(24)]
            bonsai.sky_pane(canvas, hour)
            roles = {ink for row in canvas for _, ink in row}
            self.assertGreater(len(roles & set(noon)), 5)

    def test_celestial_bodies_remain_in_the_time_selected_corner(self):
        for hour in (0, 5.999, 6, 11.999, 12, 17.999, 18, 23.999):
            canvas = [[(' ', '') for _ in range(57)] for _ in range(24)]
            bonsai.sky_pane(canvas, hour)
            body = [(x, y) for y, row in enumerate(canvas)
                    for x, (_, ink) in enumerate(row)
                    if ink.startswith(('sky_orb', 'sky_glow'))]
            left = 6 <= hour < 12 or 18 <= hour < 24
            self.assertTrue(body)
            self.assertTrue(all((2 <= x <= 14 if left else 42 <= x <= 54)
                                and 1 <= y <= 7 for x, y in body))
            # Keep the central tree area free of celestial blocks.
            self.assertFalse(any(15 <= x <= 41 for x, y in body))

    def test_celestial_materials_and_fixed_solid_crescent(self):
        for daylight in (True, False):
            marks = bonsai.celestial_marks(daylight, True)
            body = [glyph for x, y, glyph, ink in marks if ink.startswith('sky_orb')]
            self.assertIn('█', body)
            self.assertTrue(set(body) <= {'█', '▀', '▄'})
            self.assertNotIn('☼', body)
            self.assertGreater(len({ink for x, y, glyph, ink in marks}), 3)
        moon = bonsai.celestial_marks(False, True)
        setting = bonsai.celestial_marks(False, False)
        self.assertEqual(moon, setting)
        self.assertEqual(len(set(bonsai.moon_palette().values())), 8)

    def test_cloud_weather_patterns_are_stable_connected_and_distinct(self):
        patterns = {'clear': 0, 'mega': 1, 'cumulus': 1, 'scattered': 3,
                    'cirrus': 3, 'stratus': 2, 'layered': 2}
        silhouettes = set()
        for rising in (True, False):
            for kind, expected in patterns.items():
                for seed in range(20):
                    marks = bonsai.cloud_marks(rising, seed, kind)
                    self.assertEqual(marks, bonsai.cloud_marks(rising, seed, kind))
                    self.assertEqual(bool(marks), kind != 'clear')
                    silhouettes.add(tuple((x, y, glyph) for x, y, glyph, _ in marks))
                    self.assertTrue(all(1 <= x <= 55 and 1 <= y <= 7
                                        for x, y, _, _ in marks))
                    self.assertTrue(all(ink in bonsai.cloud_palette(12)
                                        for _, _, _, ink in marks))
                    if kind == 'mega':
                        self.assertGreaterEqual(len({x for x, _, _, _ in marks}), 24)
                        self.assertGreaterEqual(len({y for _, y, _, _ in marks}), 5)
                    pixels = {(x, y * 2 + half) for x, y, glyph, _ in marks
                              for half in (0, 1)
                              if glyph == '█' or glyph == ('▀' if half == 0 else '▄')}
                    components = 0
                    while pixels:
                        pending = [pixels.pop()]
                        components += 1
                        bottom_by_column = {}
                        while pending:
                            x, y = pending.pop()
                            bottom_by_column[x] = max(y, bottom_by_column.get(x, y))
                            for neighbor in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                                if neighbor in pixels:
                                    pixels.remove(neighbor)
                                    pending.append(neighbor)
                        self.assertEqual(len(set(bottom_by_column.values())), 1,
                                         (kind, seed, 'cloud base must stay level'))
                    self.assertEqual(components, expected, (kind, seed))
        self.assertGreater(len(silhouettes), 100)
        # Automatic selection includes empty and single/multiple cloud scenes.
        selected = [bonsai.cloud_marks(True, seed) for seed in range(100)]
        self.assertTrue(any(not marks for marks in selected))
        self.assertTrue(any(marks for marks in selected))

    def test_billowing_clouds_have_multiple_distinct_peaks(self):
        for kind in ('cumulus', 'mega'):
            for seed in range(100):
                tops = {}
                for x, y, glyph, _ in bonsai.cloud_marks(True, seed, kind):
                    top = y * 2 + (glyph == '▄')
                    tops[x] = min(top, tops.get(x, top))
                # Collapse plateaus before counting separate upward puffs.
                contour = []
                for x in sorted(tops):
                    if not contour or contour[-1] != tops[x]:
                        contour.append(tops[x])
                peaks = sum(a > b < c for a, b, c in
                            zip(contour, contour[1:], contour[2:]))
                self.assertGreaterEqual(peaks, 2, (kind, seed, contour))

    def test_cloud_palette_has_soft_light_and_cool_shadow(self):
        import re
        def rgb(ink):
            return tuple(map(int, re.findall(r'\d+', ink)[-3:]))
        for hour in (0, 6, 9, 12, 17, 23):
            shades = [rgb(bonsai.cloud_palette(hour)[f'sky_cloud{i}'])
                      for i in range(6)]
            self.assertEqual(len(set(shades)), 6)
            self.assertTrue(all(sum(a) > sum(b) for a, b in zip(shades, shades[1:])))
            self.assertGreater(shades[-1][2], shades[-1][0])
        dawn = rgb(bonsai.cloud_palette(6)['sky_cloud0'])
        night = rgb(bonsai.cloud_palette(23)['sky_cloud0'])
        self.assertGreater(dawn[0], dawn[2])
        self.assertGreater(night[2], night[0])
        self.assertEqual(bonsai.cloud_palette(0), bonsai.cloud_palette(24))

    def test_clouds_match_lighting_and_preserve_foreground(self):
        cases = ((hour, kind) for hour in (3, 6, 9, 12, 17, 21)
                 for kind in ('clear', 'mega', 'cumulus', 'scattered',
                              'cirrus', 'stratus', 'layered'))
        for hour, kind in cases:
            canvas = bonsai.specimen_canvas(30, 42, 'informal', 42)
            foreground = {(x, y): cell for y, row in enumerate(canvas)
                          for x, cell in enumerate(row) if cell[1]}
            rising = 6 <= hour < 12 or hour >= 18
            marks = bonsai.cloud_marks(rising, 42, kind)
            with patch.object(bonsai, 'cloud_marks', return_value=marks):
                bonsai.sky_pane(canvas, hour)
            clouds = [(x, y, glyph, ink) for y, row in enumerate(canvas)
                      for x, (glyph, ink) in enumerate(row)
                      if ink.startswith('sky_cloud')]
            self.assertEqual(bool(clouds), kind != 'clear')
            self.assertTrue(all(1 <= x <= 55 and 1 <= y <= 8
                                and glyph in '█▀▄' for x, y, glyph, ink in clouds))
            self.assertTrue(all(ink in bonsai.cloud_palette(hour)
                                for x, y, glyph, ink in clouds))
            for (x, y), cell in foreground.items():
                self.assertEqual(canvas[y][x], cell)
            for x, y, _, _ in clouds:
                self.assertFalse(any((x + dx, y + dy) in foreground
                                     for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))))
        self.assertNotEqual(bonsai.cloud_palette(12), bonsai.cloud_palette(21))
        self.assertNotEqual(bonsai.cloud_palette(6), bonsai.cloud_palette(12))

    def test_tree_occlusion_removes_small_cloud_islands(self):
        canvas = [[(' ', '') for _ in range(57)] for _ in range(24)]
        # A continuous bank is cut into a substantial cloud and a tiny speck.
        marks = [(x, 8, '█', 'sky_cloud2') for x in range(15, 27)]
        canvas[8][23] = ('│', 'bark')
        with patch.object(bonsai, 'cloud_marks', return_value=marks):
            bonsai.sky_pane(canvas, 12)
        self.assertTrue(all(canvas[8][x][1] == 'sky_cloud2' for x in range(15, 22)))
        self.assertEqual(canvas[8][23], ('│', 'bark'))
        self.assertEqual(canvas[8][25:27], [(' ', ''), (' ', '')])

    def test_cloud_fragments_use_half_block_connectivity(self):
        canvas = [[(' ', '') for _ in range(57)] for _ in range(24)]
        marks = [(x, 8, '█', 'sky_cloud2') for x in range(15, 20)]
        # Opposite half-blocks in neighboring columns do not touch.
        marks += [(25, 8, '▀', 'sky_cloud2'), (26, 8, '▄', 'sky_cloud2')]
        with patch.object(bonsai, 'cloud_marks', return_value=marks):
            bonsai.sky_pane(canvas, 12)
        self.assertEqual(canvas[8][25:27], [(' ', ''), (' ', '')])
        self.assertTrue(all(canvas[8][x][1] == 'sky_cloud2' for x in range(15, 20)))

    def test_crescent_negative_space_is_clear_of_stars(self):
        for hour in (3, 21):
            canvas = [[(' ', '') for _ in range(57)] for _ in range(24)]
            bonsai.sky_pane(canvas, hour)
            cx = 8 if hour == 21 else 48
            self.assertFalse(any(ink == 'sky_star' and abs(x - cx) <= 7 and abs(y - 4) <= 4
                                 for y, row in enumerate(canvas) for x, (_, ink) in enumerate(row)))

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
                    self.assertIn('╭══════════┴══════════╮'.encode(), plain)
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

    def test_rounded_backing_and_border_share_a_clipped_pixel_mask(self):
        import struct
        import zlib
        png = bonsai.rounded_frame_png(10, 20, 26, (240, 130, 80), (18, 52, 86))
        self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
        width, height = struct.unpack('!II', png[16:24])
        self.assertEqual((width, height), (590, 520))
        offset, compressed = 8, b''
        while offset < len(png):
            size = struct.unpack('!I', png[offset:offset + 4])[0]
            if png[offset + 4:offset + 8] == b'IDAT':
                compressed += png[offset + 8:offset + 8 + size]
            offset += size + 12
        pixels = zlib.decompress(compressed)
        def pixel(x, y):
            start = y * (width * 4 + 1) + 1 + x * 4
            return tuple(pixels[start:start + 4])
        self.assertEqual(pixel(295, 0)[3], 0, 'no dark strip above the top edge')
        self.assertEqual(pixel(5, 10)[3], 0, 'outside the rounded corner stays transparent')
        self.assertEqual(pixel(295, 10), (240, 130, 80, 255))
        self.assertEqual(pixel(295, 260), (18, 52, 86, 255), 'keep the center quiet')
        self.assertGreater(pixel(10, 150)[2], 86, 'cool reflection defines the side pane')
        self.assertEqual(pixel(30, 150), (18, 52, 86, 255), 'optics stay outside the artwork')
        self.assertEqual(pixel(584, 260), (240, 130, 80, 255))
        self.assertEqual(pixel(589, 260)[3], 0)
        for x in (5, 584):
            self.assertEqual(pixel(x, 260)[3], 255, 'glass wall stays in place')
            self.assertEqual(pixel(x, 493)[3], 0, 'upper tier has a visible setback')
            self.assertGreater(pixel(x, 502)[3], 0, 'middle tier projects past upper tier')
        for x in (7, 582):
            self.assertGreater(pixel(x, 493)[3], 0, 'chamfer joins glass to the upper tier')
        for x in (10, 579):
            for y in range(486, 499):
                self.assertEqual(pixel(x, y)[3], 255, 'glass seat has no open seam')
        for x in (1, 588):
            self.assertEqual(pixel(x, 502)[3], 0, 'middle tier has a visible setback')
            self.assertGreater(pixel(x, 510)[3], 0, 'bottom tier projects past middle tier')
        self.assertEqual(pixel(1, 510)[3], pixel(588, 510)[3])
        self.assertEqual({pixel(295, y)[:3] for y in range(499, 518)},
                         {(20, 23, 25)}, 'all tier faces share one dark charcoal color')
        for x in (5, 584):
            self.assertEqual(pixel(x, 510)[3], 255, 'broad bottom foot stays solid')
        self.assertEqual(pixel(295, 510)[3], 255, 'thicker plinth has a full lower face')
        self.assertLess(sum(pixel(295, 510)[:3]), sum(pixel(295, 498)[:3]),
                        'recessed lower lip stays darker than the upper bevel')
        self.assertEqual(pixel(295, 519)[3], 0, 'leave clearance below the plinth')
        self.assertEqual(pixel(295, 519)[3], 0)
        for center in (230, 340):
            self.assertNotEqual(pixel(center, 482)[:3], (18, 52, 86), 'solid ceramic neck')
            self.assertEqual(pixel(center - 14, 481)[:3], (18, 52, 86), 'narrow upper edge')
            self.assertNotEqual(pixel(center - 14, 488)[:3], (18, 52, 86), 'foot flares outward')
            self.assertEqual(pixel(center, 488)[3], 255, 'feet stay opaque')
        self.assertEqual(pixel(235, 490)[3], 255, 'floor meets the feet')
        self.assertEqual(pixel(295, 475), (18, 52, 86, 255),
                         'open space below the bowl, between the feet')
        for x in (235, 335):
            self.assertLess(sum(pixel(x, 490)[:3]), sum(pixel(295, 490)[:3]),
                            'small contact shadows sit under each foot')

    def test_wide_plinth_keeps_glass_and_feet_aligned(self):
        import struct
        import zlib
        png = bonsai.rounded_frame_png(10, 20, 26, (130, 160, 140),
                                      (18, 24, 22), overhang_cells=1)
        width, height = struct.unpack('!II', png[16:24])
        self.assertEqual((width, height), (610, 520))
        offset, compressed = 8, b''
        while offset < len(png):
            size = struct.unpack('!I', png[offset:offset + 4])[0]
            if png[offset + 4:offset + 8] == b'IDAT':
                compressed += png[offset + 8:offset + 8 + size]
            offset += size + 12
        pixels = zlib.decompress(compressed)
        def pixel(x, y):
            start = y * (width * 4 + 1) + 1 + x * 4
            return tuple(pixels[start:start + 4])
        for x in (5, 604):
            self.assertEqual(pixel(x, 260)[3], 0, 'overhang leaves glass width unchanged')
            self.assertEqual(pixel(x, 510)[3], 255, 'base extends past glass')
        for x in (15, 594):
            self.assertEqual(pixel(x, 260)[3], 255, 'glass shifts with image padding')
        for center in (240, 350):
            self.assertNotEqual(pixel(center, 485)[:3], (18, 24, 22), 'feet align with text')
        for x in (20, 589):
            for y in range(486, 499):
                self.assertEqual(pixel(x, y)[3], 255, 'seat stays connected')

    def test_glass_varies_between_seeds_and_stays_stable_within_a_session(self):
        first = bonsai.glass_reflections(11, True)
        self.assertGreater(len({bonsai.glass_reflections(seed, True) for seed in range(120)}), 40)
        self.assertEqual(first, bonsai.glass_reflections(11, True))
        for seed in range(500):
            for left_corner in (False, True):
                points = bonsai.glass_reflections(seed, left_corner)
                self.assertGreaterEqual(len(points), 4)
                self.assertLessEqual(len(points), 10)
                self.assertIn(min(y for x, y in points), (3, 7, 14))
                self.assertEqual(len(points), len(set(points)))
                self.assertTrue(all((49 <= x <= 55 if left_corner else 1 <= x <= 7)
                                    and 3 <= y <= 17 for x, y in points))

    def test_all_glass_groups_vary_and_never_overlap_each_other_or_art(self):
        horizontal_layouts = set()
        for hour in (3, 9, 15, 21):
            original = bonsai.specimen_canvas(30, 42)
            bonsai.sky_pane(original, hour)
            occupied = {(x, y) for y, row in enumerate(original)
                        for x, (_, ink) in enumerate(row) if ink}
            seen_counts, streak_sides = set(), set()
            for seed in range(60):
                canvas = [row[:] for row in original]
                groups = bonsai.place_glass_marks(canvas, seed)
                horizontal_layouts.add(tuple(points for glyph, points in groups if glyph == '─'))
                self.assertIn(len(groups), (2, 3))
                seen_counts.add(len(groups))
                streak_sides.update(points[0][0] < 28 for glyph, points in groups if glyph == '╱')
                left_count = sum(points[0][0] < 28 for _, points in groups)
                self.assertIn(left_count, (1,) if len(groups) == 2 else (1, 2))
                self.assertTrue(any(glyph == '─' for glyph, _ in groups))
                previous = set(occupied)
                for glyph, points in groups:
                    self.assertEqual(len(points), len(set(points)))
                    for x, y in points:
                        self.assertTrue(all((x + dx, y + dy) not in previous
                                            for dx in (-1, 0, 1) for dy in (-1, 0, 1)))
                        self.assertEqual(canvas[y][x][0], glyph)
                    previous.update(points)
                for x, y in occupied:
                    self.assertEqual(canvas[y][x], original[y][x])
            self.assertEqual(seen_counts, {2, 3})
            self.assertEqual(streak_sides, {False, True})
        self.assertGreater(len(horizontal_layouts), 20)
        full = [[('█', 'wood') for _ in range(57)] for _ in range(24)]
        self.assertEqual(bonsai.place_glass_marks(full, 42), [])

    def test_kitty_frame_is_quiet_and_preserves_the_terminal_cursor(self):
        import struct
        with patch.dict(os.environ, {'TERM': 'xterm-kitty'}), \
             patch.object(bonsai.sys.stdout, 'isatty', return_value=True), \
             patch.object(bonsai.sys.stdout, 'fileno', return_value=1), \
             patch.object(bonsai.fcntl, 'ioctl', return_value=struct.pack('HHHH', 40, 80, 800, 800)):
            command = bonsai.kitty_frame(26, 80, [240, 130, 80])
            self.assertEqual(command, bonsai.kitty_frame(26, 80, [240, 130, 80]))
            self.assertIn('q=2,z=-1,C=1,c=61,r=26', command)
            self.assertTrue(command.startswith('\033[9C'))
            self.assertTrue(command.endswith('\033[9D'))
            compact = bonsai.kitty_frame(26, 60, [240, 130, 80])
            self.assertIn('C=1,c=59,r=26', compact)
        with patch.dict(os.environ, {'TERM': 'xterm-kitty'}), \
             patch.object(bonsai.sys.stdout, 'isatty', return_value=False):
            self.assertEqual(bonsai.kitty_frame(26, 80, [240, 130, 80]), '')

    def test_flat_base_touches_the_pot(self):
        for seed in range(16):
            rows = bonsai.render(30, seed, False, 59, fixed_height=True).splitlines()
            self.assertEqual(rows[0], "╭" + "─" * 57 + "╮")
            self.assertEqual(rows[-2], "├" + "─" * 20 + "▟██▙" + "─" * 7 + "▟██▙" + "─" * 22 + "┤")
            foot = bonsai.pot_rows(seed)[-1]
            self.assertIn(foot.strip(), rows[-3])
            for column, glyph in enumerate(rows[-2]):
                if glyph == "█":
                    self.assertEqual(rows[-3][column], "┯")
            for column, glyph in enumerate(rows[-2]):
                if glyph in "▟▙":
                    self.assertNotEqual(rows[-3][column], "┯")
            self.assertTrue(rows[-3][1:-1].strip())
            self.assertNotIn("╱", rows[0])

    def test_frame_fits_and_keeps_animation_height(self):
        for columns in (59, 80, 100):
            for day in (0, 7, 30):
                image = bonsai.render(day, 42, False, columns,
                                     ['#85b470'] * 3, fixed_height=True)
                rows = image.splitlines()
                self.assertEqual(len(rows), 26)
                self.assertEqual(rows[0].strip(), "╭" + "─" * 57 + "╮")
                self.assertEqual(rows[-1].strip(), "╰" + "─" * 57 + "╯")
                self.assertNotIn('║', image)
                left = len(rows[0]) - 59
                self.assertLessEqual(abs(left - (columns - len(rows[0]))), 1)
                self.assertEqual(len({len(row) for row in rows}), 1)
                self.assertTrue(all(len(row) <= columns for row in rows))
                self.assertNotIn('\033', image)

    def test_terrarium_preserves_tree_and_terminal_background(self):
        import re
        canvas = bonsai.specimen_canvas(30, 42)
        image = bonsai.render(30, 42, True, 59, fixed_height=True, hour=15)
        plain = re.sub(r'\x1b\[[0-9;]*m', '', image).splitlines()
        self.assertEqual(len(plain), 26)
        self.assertTrue(all(len(row) == 59 for row in plain))
        for y, row in enumerate(canvas):
            for x, (glyph, ink) in enumerate(row):
                if glyph != ' ':
                    self.assertEqual(plain[y + 1][x + 1], glyph)
        self.assertIn("\033[48;2;{};{};{}m".format(*bonsai.theme_background()), image)
        self.assertTrue(any(plain[y + 1][x + 1] == '╱' and cell == (' ', '')
                            for y, row in enumerate(canvas) for x, cell in enumerate(row)))

    def test_terrarium_keeps_theme_backing_inside_the_frame(self):
        import re
        expected_background = bonsai.theme_background()
        for theme in (['#fafafa'] * 3, ['#111111'] * 3, ['#fa4050'] * 3):
            for day in (0, 30):
                for hour in (0, 6, 12, 18):
                    image = bonsai.render(day, 42, True, 80, theme,
                                          fixed_height=True, hour=hour)
                    for y, row in enumerate(image.splitlines()):
                        background, column = None, 0
                        for token in re.split(r'(\x1b\[[0-9;]*m)', row):
                            if token.startswith('\x1b['):
                                codes = list(map(int, token[2:-1].split(';')))
                                if codes[0] == 0:
                                    background = None
                                if codes[:2] == [48, 2]:
                                    background = tuple(codes[2:])
                            else:
                                for glyph in token:
                                    inside = 10 <= column < 69
                                    expected = expected_background if inside else None
                                    self.assertEqual(background, expected)
                                    column += 1
                        self.assertEqual(column, 69)
                        self.assertIsNone(background, 'reset the backing before the prompt')
                    plain = bonsai.render(day, 42, False, 80, theme, fixed_height=True, hour=hour)
                    self.assertNotIn('\033', plain)
                    for row in plain.splitlines()[1:-2]:
                        self.assertEqual((row[10], row[-1]), ('│', '│'))

    def test_sky_follows_local_time_and_preserves_specimen(self):
        import re
        for hour in (0, 12):
            image = bonsai.render(0, 42, False, 59, fixed_height=True, hour=hour)
            self.assertIn('·', image)
            self.assertNotIn('☼', image)
            self.assertNotIn('☾', image)
            self.assertEqual(len(image.splitlines()), 26)
            self.assertTrue(all(len(row) == 59 for row in image.splitlines()))
        for hour in range(24):
            canvas = bonsai.specimen_canvas(30, 42)
            original = [row[:] for row in canvas]
            bonsai.sky_pane(canvas, hour)
            for y, row in enumerate(original):
                for x, cell in enumerate(row):
                    if cell != (' ', ''):
                        self.assertEqual(canvas[y][x], cell)
        local = __import__('time').struct_time((2026, 11, 15, 12, 0, 0, 6, 319, -1))
        with patch.object(bonsai.time, 'localtime', return_value=local):
            self.assertEqual(bonsai.render(0, 42), bonsai.render(0, 42, hour=12))

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

    @patch.object(bonsai, "transparency_lift", return_value=0)
    def test_green_leaves_get_brown_wood_and_red_leaves_get_red_wood(self, _lift):
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

    def test_leaf_base_preserves_actual_theme_colors(self):
        import re
        def rgb(ink):
            return tuple(map(int, re.findall(r'\d+', ink)[-3:]))
        # Pastels, dark colors and neutrals must not acquire forced saturation
        # or brightness; the middle shade is the source color exactly.
        for color in ('#70bb50', '#6080dc', '#db6095', '#eeeeee', '#15121b', '#e5bcc4', '#000000'):
            palette = bonsai.specimen_palette(42, [color] * 3)
            expected = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
            self.assertEqual(rgb(palette['leaf4']), expected)
            self.assertEqual(palette['leaf'], palette['leaf4'])
            for group in range(3):
                shadow, base, highlight = [rgb(palette[f'leaf{group*3+j}']) for j in range(3)]
                self.assertEqual(base, expected)
                self.assertTrue(all(a <= b <= c for a,b,c in zip(shadow,base,highlight)))
        neutral = bonsai.specimen_palette(42, ['#888888', '#ff0000', '#00ff00'])
        self.assertTrue(all(len(set(rgb(neutral[f'leaf{i}']))) == 1 for i in range(9)))

    def test_two_wallpaper_accents_color_foliage_and_ceramics(self):
        import colorsys
        import re
        def hue(ink):
            rgb = [int(v) / 255 for v in re.findall(r'\d+', ink)[-3:]]
            return colorsys.rgb_to_hsv(*rgb)[0]
        blue_green = ['#57aae6', '#80d657', '#5790e6']
        palette = bonsai.specimen_palette(42, blue_green)
        # Blue and green mix through teal, without abrupt pure-color blocks.
        hues = [hue(palette[f'leaf{i}']) for i in (4, 1, 7)]
        self.assertGreater(hues[0], hues[1])
        self.assertGreater(hues[1], hues[2])
        self.assertTrue(all(.25 < h < .65 for h in hues))
        self.assertLess(max(abs(a-b) for a, b in zip(hues, hues[1:])), .15)
        for i in range(9):
            rgb = [int(v) / 255 for v in re.findall(r'\d+', palette[f'leaf{i}'])[-3:]]
            saturation = colorsys.rgb_to_hsv(*rgb)[1]
            self.assertGreater(saturation, .2)
            # A small secondary tint stays near the actual primary saturation.
            self.assertLessEqual(saturation, .65)
        self.assertEqual(palette['pot_inlay'], '\033[0;38;2;{};{};{}m'.format(
                    *(int(blue_green[0][i:i+2], 16) for i in (1, 3, 5))))
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
            self.assertIn(palette['ceramic_rim_11'], colored)
            self.assertIn(palette['ceramic_foot_11'], colored)
            self.assertIn(palette['ceramic_inlay_main'], colored)

    @patch.object(bonsai, "transparency_lift", return_value=0)
    def test_ceramic_uses_two_solid_enamels_and_a_subdued_bowl(self, _lift):
        import re
        from unittest.mock import patch
        def rgb(ink):
            return tuple(map(int, re.findall(r'\d+', ink)[-3:]))
        accents = ('#e65773', '#57c6e6', '#e6bb57')
        palette = bonsai.ceramic_palette(accents)
        main, accent = [rgb(palette[f'ceramic_inlay_{name}']) for name in ('main', 'accent')]
        self.assertGreater(main[0], main[2])
        self.assertGreater(accent[2], accent[0])
        self.assertTrue(all(max(color) > 180 for color in (main, accent)))
        for column in range(23):
            levels = [max(rgb(palette[f'ceramic_{material}_{column}']))
                      for material in ('foot', 'body', 'rim')]
            self.assertEqual(levels, sorted(levels))
            for material in ('foot', 'body', 'rim'):
                ceramic = rgb(palette[f'ceramic_{material}_{column}'])
                self.assertLessEqual(max(ceramic), 87)
                self.assertLessEqual(max(ceramic) - min(ceramic), 9)
        # Every complete panel uses both inks, and never interpolates between them.
        for seed in range(80):
            canvas = bonsai.specimen_canvas(30, seed)
            inks = {ink for row in canvas[20:22] for glyph, ink in row if glyph.strip()}
            self.assertTrue({'pot_inlay', 'pot_pattern'} <= inks)
            with patch.object(bonsai, 'terminal_leaf_palette', return_value=list(accents)):
                rows = bonsai.render(30, seed, True, 59, fixed_height=True).splitlines()[21:23]
            bright = {rgb(ink) for row in rows for ink in re.findall(r'\x1b\[[0-9;]*m', row)
                      if len(re.findall(r'\d+', ink)) >= 5 and max(rgb(ink)) > 100}
            frame_ink = rgb(re.findall(r"\x1b\[0;38;2;[0-9;]*m", rows[0])[0])
            self.assertEqual(bright - {frame_ink}, {main, accent})
        neutral = bonsai.ceramic_palette(('#eeeeee', '#111111', '#888888'))
        self.assertTrue(all(len(set(rgb(ink))) == 1 for ink in neutral.values()))

    def test_pot_ornaments_have_space_and_hold_still_through_growth(self):
        for seed in range(80):
            rows = bonsai.pot_rows(seed)
            for row in rows[1:3]:
                interior = row.strip()[1:-1]
                self.assertTrue(interior.startswith(' '))
                self.assertTrue(interior.endswith(' '))
                self.assertGreaterEqual(sum(c != ' ' for c in interior), 13)
            early = bonsai.specimen_canvas(0, seed)
            mature = bonsai.specimen_canvas(30, seed)
            self.assertEqual(early[20:23], mature[20:23])

    def test_main_color_outweighs_accent_in_leaves(self):
        import re
        palette = bonsai.specimen_palette(42, ['#e64040', '#40e640', '#e64040'])
        # Opposing red/green inputs expose the blend's actual weighting:
        # main must remain stronger at every shade, including accent patches.
        for i in range(9):
            red, green, blue = map(int, re.findall(r'\d+', palette[f'leaf{i}'])[-3:])
            self.assertGreater(red, green)
            self.assertGreaterEqual(green, blue)

    @patch.object(bonsai, "transparency_lift", return_value=0)
    def test_dark_wood_and_vibrant_pot_patterns(self, _lift):
        import colorsys
        import re
        for accent in ('#70bb50', '#6080dc', '#db6095', '#eeeeee'):
            for seed in range(30):
                palette = bonsai.specimen_palette(seed, [accent] * 3)
                self.assertEqual(palette['pot_inlay'], '\033[0;38;2;{};{};{}m'.format(
                    *(int(accent[i:i+2], 16) for i in (1, 3, 5))))
                self.assertNotEqual(palette['pot_shadow'], palette['leaf0'])
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
            # Inspect exposed young wood before the mature crown can shade it.
            young = bonsai.render(14, seed)
            self.assertTrue(any(bonsai.specimen_palette(seed)[name] in young
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
                self.assertEqual(palette['pot_inlay'], '\033[0;38;2;{};{};{}m'.format(
                    *(int('#e5bcc4'[i:i+2], 16) for i in (1, 3, 5))))

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
                    pot_inlay = bonsai.specimen_palette(seed)['ceramic_inlay_main']
                    self.assertIn(pot_inlay, image)
                    self.assertIn('\033[48;2;15;15;15m', image)
                    self.assertIn(bonsai.wood_palette(seed)['bark'], image)
                    self.assertEqual(state.read_text(), original)

    def test_branch_plans_vary_and_repeat_by_seed(self):
        layouts = set()
        for seed in range(48):
            layout = bonsai.branch_layout(seed)
            expected = tuple(layout)
            bonsai.branch_layout.cache_clear()
            self.assertEqual(expected, tuple(bonsai.branch_layout(seed)))
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

    def test_crown_options_vary_independently_and_use_every_scaffold(self):
        forms = set()
        counts = set()
        pairs = set()
        for seed in range(160):
            forms.add(bonsai.crown_form(seed))
            pairs.add((bonsai.growth_pattern(seed)[0], bonsai.crown_form(seed)))
            layout = bonsai.branch_layout(seed)
            counts.add(len(layout))
            self.assertTrue(5 <= len(layout) <= 9)
            roots = [b for b in bonsai.branch_graph(seed) if b['parent'] is None]
            self.assertEqual(len(roots), len(layout))
            expected = tuple(layout)
            bonsai.branch_layout.cache_clear()
            self.assertEqual(expected, tuple(bonsai.branch_layout(seed)))
            self.assertGreater(len({round(b['end'][1]) for b in roots}), 2)
        self.assertEqual(forms, set(bonsai.CROWN_FORMS))
        self.assertEqual(counts, {5,6,7,8,9})
        self.assertGreater(len(pairs), 35)

    def test_branch_hierarchy_has_staggered_connected_tapered_forks(self):
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
            self.assertLessEqual(len(graph), 5 * len(bonsai.branch_layout(seed)))
            self.assertEqual(sum(b['parent'] is None for b in graph), len(bonsai.branch_layout(seed)))
            self.assertGreaterEqual(len(descendants), 2)
            for children in descendants.values():
                self.assertLessEqual(len(children), 2)
                if len(children) == 2:
                    self.assertGreater(children[1]['attachment'] - children[0]['attachment'], .15)
                for child in children:
                    source = graph[child['parent']]
                    self.assertEqual(child['level'], source['level'] + 1)
                    self.assertLessEqual(child['level'], 2)
                    self.assertGreater((child['end'][0] - child['start'][0]) *
                                       (source['end'][0] - source['start'][0]), 0)

    def test_mature_limbs_curve_without_downward_hooks(self):
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
                # A whole-row bow on a shallow limb creates an inverted U.
                # Keep a restrained arc and never descend again near the tip.
                self.assertGreater(abs(mid[1] - straight_mid), .1)
                ys = [bonsai.branch_point(branch, i / 32)[1] for i in range(33)]
                self.assertTrue(all(b <= a + 1e-9 for a, b in zip(ys, ys[1:])))
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

    def test_every_mature_branch_tip_has_foliage(self):
        for seed in range(80):
            leaves = {(x, y) for x, y, born, glyph, ink in
                      bonsai.natural_specimen(seed, 30) if ink.startswith('leaf')}
            for branch in bonsai.branch_graph(seed):
                x, y = branch['end']
                self.assertIn((round(x), round(y)), leaves, (seed, branch))

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
        self.assertGreater(checked, 30)

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
                canvas = bonsai.specimen_canvas(day, seed)
                # Glass reflections are separate from the living silhouette.
                points = {(x,y) for y,row in enumerate(rows)
                          for x,char in enumerate(row[1:-1])
                          if char != ' ' and canvas[y][x][0] != ' '}
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

    def test_lateral_scaffolds_have_bounded_reach_and_rising_tips(self):
        for seed in range(80):
            for branch in bonsai.branch_graph(seed):
                if branch['parent'] is not None or branch['leader'] or branch.get('lower'):
                    continue
                x,y = branch['start']
                tx,ty = branch['end']
                self.assertLessEqual(abs(tx-x), 13+1e-8)
                self.assertLess(ty,y)

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

    def test_lower_shoots_removed_and_blossoms_are_spaced_and_stable(self):
        for seed in range(64):
            self.assertFalse(any(branch.get('lower') for branch in bonsai.branch_graph(seed)))
            sites = bonsai.blossom_sites(seed)
            self.assertEqual(sites, bonsai.blossom_sites(seed))
            self.assertTrue(2 <= len(sites) <= 4)
            for x,y,born in sites:
                self.assertTrue(21 <= born <= 26)
            for i,(x,y,born) in enumerate(sites):
                self.assertTrue(all(max(abs(x-px),abs(y-py)) >= 3 for px,py,_ in sites[i+1:]))

    def test_flowers_match_the_rendered_pot_accent(self):
        from unittest.mock import patch
        for accent in ('#57aae6', '#e5bcc4', '#15121b'):
            theme = ['#85b470', accent, '#67bca3']
            expected = bonsai.ceramic_palette(tuple(theme))['ceramic_inlay_accent']
            self.assertEqual(bonsai.specimen_palette(42, theme)['blossom'], expected)
            with patch.object(bonsai, 'terminal_leaf_palette', return_value=theme):
                image = bonsai.render(30, 42, True, 59)
            import re
            foreground_only = re.sub(r'\x1b\[48;2;[0-9;]+m', '', image)
            self.assertTrue(any(expected + glyph in foreground_only
                                for glyph in bonsai.BLOSSOM_FORMS))

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
                self.assertIn(canvas[y][x][0], bonsai.BLOSSOM_FORMS)
                self.assertEqual(canvas[y][x][1], 'blossom')
            blank = [[(' ', '') for _ in range(57)] for _ in range(24)]
            bonsai.add_blossoms(blank,seed,30)
            self.assertTrue(all(glyph == ' ' for row in blank for glyph,ink in row))

    def test_rosette_sprays_open_in_stages_and_preserve_the_canopy(self):
        shapes = set()
        for seed in range(12):
            sites = bonsai.blossom_sites(seed)
            x,y,born = sites[0]
            original = [[('●', 'leaf1') for _ in range(57)] for _ in range(24)]
            original[y][x-1] = ('│', 'wood')
            original[y-1][x] = (' ', '')
            snapshots = []
            for day in (born, born + 0.8, 30):
                canvas = [row.copy() for row in original]
                bonsai.add_blossoms(canvas,seed,day)
                snapshots.append(canvas)
                self.assertEqual(canvas[y][x-1], ('│', 'wood'))
                self.assertEqual(canvas[y-1][x], (' ', ''))
            self.assertEqual(snapshots[0][y][x][0], '✦')
            self.assertEqual(snapshots[1][y][x][0], '❀')
            shapes.add(snapshots[2][y][x][0])
            flowers = [(px,py) for py,row in enumerate(snapshots[2])
                       for px,(glyph,ink) in enumerate(row) if ink == 'blossom']
            self.assertGreater(len(flowers),len(sites))
            self.assertTrue(all(any(max(abs(px-sx),abs(py-sy)) <= 4 for sx,sy,_ in sites)
                                for px,py in flowers))
            again = [row.copy() for row in original]
            bonsai.add_blossoms(again,seed,30)
            self.assertEqual(again,snapshots[2])
        self.assertGreaterEqual(len(shapes),3)

    def test_every_blossom_stays_spaced_even_as_later_buds_open(self):
        for style in ('informal', 'natural', 'slant', 'semi-cascade'):
            for seed in range(32):
                plan = bonsai.blossom_plan(seed,style)
                self.assertEqual(plan,bonsai.blossom_plan(seed,style))
                # Include unopened flowers: companions cannot take their space.
                for i,(x,y,born,glyph) in enumerate(plan):
                    self.assertTrue(all(max(abs(x-px),abs(y-py)) >= 3
                                        for px,py,_,_ in plan[i+1:]), (style,seed))
                for day in (21,24,27,30):
                    canvas = [[('●','leaf1') for _ in range(57)] for _ in range(24)]
                    bonsai.add_blossoms(canvas,seed,day,style)
                    actual = [(x,y) for y,row in enumerate(canvas)
                              for x,(glyph,ink) in enumerate(row) if ink == 'blossom']
                    self.assertEqual(set(actual), {(x,y) for x,y,born,_ in plan if born <= day})
                    for i,(x,y) in enumerate(actual):
                        self.assertTrue(all(max(abs(x-px),abs(y-py)) >= 3
                                            for px,py in actual[i+1:]), (style,seed,day))
                if seed < 8:
                    canvas = bonsai.specimen_canvas(30,seed,style)
                    actual = [(x,y) for y,row in enumerate(canvas)
                              for x,(glyph,ink) in enumerate(row) if ink == 'blossom']
                    self.assertTrue(actual)
                    self.assertTrue(set(actual) <= {(x,y) for x,y,_,_ in plan})

    def test_actual_blossom_rendering_keeps_early_growth_clean(self):
        flowering = 0
        for seed in range(48):
            early = bonsai.render(10,seed,False,80,['#85b470']*3)
            self.assertFalse(any(glyph in early for glyph in bonsai.BLOSSOM_FORMS))
            mature = bonsai.render(30,seed,False,80,['#85b470']*3)
            count = sum(mature.count(glyph) for glyph in bonsai.BLOSSOM_FORMS)
            self.assertLessEqual(count,8)
            flowering += count > 0
        self.assertEqual(flowering,48)
        for style in ('natural', 'slant', 'semi-cascade'):
            for seed in range(12):
                image = bonsai.render(30,seed,False,59,style=style)
                self.assertTrue(1 <= sum(image.count(glyph) for glyph in bonsai.BLOSSOM_FORMS) <= 8, (style,seed))

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

    def test_fan_crowns_fill_the_inner_funnel_with_supported_foliage(self):
        for seed in (1,7,17,33):
            canvas = bonsai.specimen_canvas(30,seed)
            center = round(bonsai.trunk_path(seed)[6])
            filled = sum(canvas[y][x][1].startswith('leaf') or canvas[y][x][1] == 'blossom'
                         for y in range(7,12) for x in range(center-3,center+4))
            self.assertGreaterEqual(filled,20,seed)
            self.assertTrue(any(ink in ('wood','woodlight','bark','scar')
                                for row in canvas[15:19] for glyph,ink in row if glyph.strip()))
            graph = bonsai.branch_graph(seed)
            shoots = [spray for spray in bonsai.foliage_sprays(seed) if spray.get('inner')]
            self.assertTrue(shoots)
            for shoot in shoots:
                support = graph[shoot['support']]
                self.assertEqual(shoot['end'], bonsai.branch_point(support,shoot['attachment']))
                self.assertEqual(shoot['born'],support['born'])

    def test_fan_forms_have_curved_wood_and_fuller_lower_shoulders(self):
        # Representative broom and oak crowns previously had a nearly straight
        # base and narrow, isolated pads above long exposed scaffold arms.
        for seed in (1,4,7,17):
            self.assertIn(bonsai.growth_pattern(seed)[0], ('broom', 'old_oak'))
            canvas = bonsai.specimen_canvas(30,seed)
            foliage = [(x,y) for y,row in enumerate(canvas[:19])
                       for x,(glyph,ink) in enumerate(row)
                       if ink.startswith('leaf') or ink == 'blossom']
            self.assertGreaterEqual(sum(y >= 8 for x,y in foliage), 40)
            roots = [branch for branch in bonsai.branch_graph(seed) if branch['parent'] is None]
            self.assertGreater(max(abs(bonsai.branch_point(branch,.5)[1]
                                       - (branch['start'][1] + branch['end'][1])/2)
                                   for branch in roots[:3]), 1.1)
            base = bonsai.trunk_path(seed)[:7]
            self.assertGreater(max(base)-min(base), 1.5)

    def test_broom_is_retained_and_twin_leader_removed(self):
        broom_count = 0
        for seed in range(120):
            habit, side = bonsai.growth_pattern(seed)
            self.assertNotEqual(habit,'twin_leader')
            if habit != 'broom':
                continue
            broom_count += 1
            roots = [branch for branch in bonsai.branch_graph(seed) if branch['parent'] is None]
            self.assertEqual(len(roots),len(bonsai.branch_layout(seed)))
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
            self.assertEqual(len(roots),len(bonsai.branch_layout(seed)))
            self.assertEqual([branch['width'] for branch in roots[:3]],[1.25,1.1,.9])
            self.assertTrue(all(branch['start'][1] >= 11 for branch in roots))
        self.assertGreater(checked,10)

    def test_twisted_juniper_has_multiple_supported_foliage_tiers(self):
        checked = 0
        for seed in range(160):
            if bonsai.growth_pattern(seed)[0] != 'twisted_juniper':
                continue
            checked += 1
            path = bonsai.trunk_path(seed)
            self.assertGreater(max(path)-min(path),3.5)
            graph = bonsai.branch_graph(seed)
            pads = [branch for branch in graph if branch['parent'] is None]
            self.assertTrue(5 <= len(pads) <= 9)
            self.assertEqual(len(pads),len(bonsai.branch_layout(seed)))
            self.assertGreater(max(b['start'][1] for b in pads) - min(b['start'][1] for b in pads), 4)
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
            self.assertIn('╭══════════┴══════════╮', result.stdout)
            self.assertNotIn('\033', result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])

    @unittest.skipUnless(__import__('shutil').which('fish'), 'Fish is required')
    def test_fish_paints_fresh_cache_before_launch_and_skips_stale_cache(self):
        import pty
        import time
        source = (SOURCE.parents[1] / '../config/fish/config.fish').resolve().read_text()
        greeting = source.split('# Finish painting')[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bonsai-grow/prepared-v20-100').mkdir(parents=True)
            (root / 'rebos_shell').mkdir()
            (root / 'bin').mkdir()
            script = root / 'bin/bonsai-grow'
            script.write_text('#!/bin/sh\nprintf "PYTHON_LAUNCH %s\\n" "$*" >&2\n')
            script.chmod(0o755)
            config = root / 'greeting.fish'
            config.write_text(greeting)
            cache = root / 'bonsai-grow/prepared-v20-100/0.ready'
            palette = root / 'rebos_shell/effective-palette.json'
            palette.write_text('{}')
            for fresh in (True, False):
                with self.subTest(fresh=fresh):
                    cache.write_text('IDENTITY\nCACHED_FRAME')
                    stamp = time.time() + (10 if fresh else -10)
                    os.utime(cache, (stamp, stamp))
                    master, slave = pty.openpty()
                    try:
                        subprocess.run(['fish', '--no-config', '-ic',
                                        f'source {config}; fish_greeting'],
                            stdin=subprocess.DEVNULL, stdout=slave, stderr=slave,
                            env={**os.environ, 'PATH': str(root / 'bin') + ':' + os.environ['PATH'],
                                 'XDG_CACHE_HOME': directory, 'COLUMNS': '100', 'LINES': '40',
                                 'TERM': 'xterm-kitty', 'REDUCE_MOTION': '0'},
                            check=True, timeout=5)
                        os.close(slave)
                        slave = None
                        output = b''
                        while True:
                            try:
                                part = os.read(master, 65536)
                            except OSError:
                                break
                            if not part:
                                break
                            output += part
                        if fresh:
                            self.assertLess(output.index(b'CACHED_FRAME'), output.index(b'PYTHON_LAUNCH'))
                            self.assertIn(b'--opening-shown', output)
                        else:
                            self.assertNotIn(b'CACHED_FRAME', output)
                            self.assertNotIn(b'--opening-shown', output)
                    finally:
                        if slave is not None:
                            os.close(slave)
                        os.close(master)

    @unittest.skipUnless(__import__('shutil').which('fish'), 'Fish is required')
    def test_concurrent_fish_launches_claim_different_prepared_specimens(self):
        import pty
        source = (SOURCE.parents[1] / '../config/fish/config.fish').resolve().read_text()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = root / 'bonsai-grow/prepared-v20-100'
            pool.mkdir(parents=True)
            (root / 'bin').mkdir()
            script = root / 'bin/bonsai-grow'
            script.write_text('#!/bin/sh\nexit 0\n')
            script.chmod(0o755)
            config = root / 'greeting.fish'
            config.write_text(source.split('# Finish painting')[0])
            for index in range(4):
                (pool / f'{index}.ready').write_text(f'IDENTITY-{index}\nSPECIMEN-{index}')
            launches = []
            try:
                for _ in range(4):
                    master, slave = pty.openpty()
                    process = subprocess.Popen(['fish', '--no-config', '-ic',
                                                f'source {config}; fish_greeting'],
                        stdin=subprocess.DEVNULL, stdout=slave, stderr=slave,
                        env={**os.environ, 'PATH': str(root / 'bin') + ':' + os.environ['PATH'],
                             'XDG_CACHE_HOME': directory, 'COLUMNS': '100', 'LINES': '40',
                             'TERM': 'xterm-kitty', 'REDUCE_MOTION': '0'})
                    os.close(slave)
                    launches.append((process, master))
                consumed = set()
                for process, master in launches:
                    process.wait(timeout=5)
                    output = b''
                    while True:
                        try:
                            part = os.read(master, 65536)
                        except OSError:
                            break
                        if not part:
                            break
                        output += part
                    matches = [index for index in range(4) if f'SPECIMEN-{index}'.encode() in output]
                    self.assertEqual(len(matches), 1, output)
                    consumed.update(matches)
                self.assertEqual(len(consumed), 4)
                self.assertEqual(list(pool.glob('*.ready')), [])
                self.assertEqual(list(pool.glob('.claimed-*')), [])
            finally:
                for process, master in launches:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    os.close(master)

    def test_greeting_starts_refill_before_returning_worker_pid(self):
        from unittest.mock import Mock
        events = []
        with patch.object(bonsai.sys, 'stderr', Mock(isatty=lambda: True, fileno=lambda: 2)), \
             patch.object(bonsai.os, 'get_terminal_size', return_value=os.terminal_size((100, 40))), \
             patch.object(bonsai, 'start_refill', side_effect=lambda *args: events.append('refill')), \
             patch.object(bonsai.os, 'fork', side_effect=lambda: events.append('worker') or 123), \
             patch('builtins.print', side_effect=lambda *args, **kwargs: events.append('pid')), \
             patch.dict(os.environ, {'TERM': 'xterm-kitty', 'REDUCE_MOTION': '0'}):
            bonsai.greeting(42, 2, 'informal')
        self.assertEqual(events, ['refill', 'worker', 'pid'])

    def test_prepared_pool_has_unique_identities_and_replaces_only_consumed_slots(self):
        import json
        accents = ['#85b470', '#b8ce93', '#67bca3']
        original_glass = bonsai.GLASS_SEED
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {'XDG_CACHE_HOME': directory}), \
             patch.object(bonsai, 'render', return_value='FRAME') as render:
            bonsai.refill_prepared(100, accents, 'informal')
            pool = bonsai.prepared_directory(100)
            files = sorted(pool.glob('*.ready'))
            self.assertEqual(len(files), 4)
            identities = [json.loads(path.read_text().splitlines()[0]) for path in files]
            for key in ('seed', 'pot_seed', 'glass_seed'):
                self.assertEqual(len({identity[key] for identity in identities}), 4)
            bonsai.refill_prepared(100, accents, 'informal')
            self.assertEqual(render.call_count, 4)
            files[0].rename(pool / '.claimed-test')
            bonsai.refill_prepared(100, accents, 'informal')
            self.assertEqual(render.call_count, 5)
            replacement = json.loads(files[0].read_text().splitlines()[0])
            self.assertNotEqual(replacement['seed'], identities[0]['seed'])
            self.assertEqual(bonsai.GLASS_SEED, original_glass)

    def test_prepared_live_frame_exactly_matches_cached_specimen(self):
        import json
        size = os.terminal_size((100, 40))
        accents = ['#85b470', '#b8ce93', '#67bca3']
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {'XDG_CACHE_HOME': directory}), \
             patch.object(bonsai, 'GLASS_SEED', bonsai.GLASS_SEED):
            bonsai.refill_prepared(100, accents, 'informal')
            header, cached = (bonsai.prepared_directory(100) / '0.ready').read_text().split('\n', 1)
            identity = bonsai.prepared_identity(header, 100, accents, 'informal')
            self.assertIsNotNone(identity)
            with patch.object(bonsai.time, 'monotonic', side_effect=[0, .2]), \
                 patch.object(bonsai.time, 'sleep'), patch('signal.signal'), \
                 patch.object(bonsai, 'start_refill') as refill, \
                 patch.object(bonsai.shutil, 'get_terminal_size', side_effect=[size, size, os.terminal_size((101, 40))]), \
                 patch.object(bonsai.os, 'write') as write:
                bonsai.animate_background(999, accents, 2, 'informal', identity)
            self.assertEqual(write.call_args.args[1], cached.encode())
            refill.assert_called_once_with(100, accents, 'informal')
            self.assertIsNone(bonsai.prepared_identity(header, 80, accents, 'informal'))
            self.assertIsNone(bonsai.prepared_identity(header, 100, ['#000000'] * 3, 'informal'))
            self.assertIsNone(bonsai.prepared_identity('broken', 100, accents, 'informal'))

    def test_cached_greeting_does_not_clear_the_opening(self):
        from unittest.mock import Mock
        terminal = Mock(isatty=lambda: True, fileno=lambda: 2)
        with patch.object(bonsai.sys, 'stderr', terminal), \
             patch.object(bonsai.os, 'get_terminal_size', return_value=os.terminal_size((100, 40))), \
             patch.object(bonsai.os, 'fork', return_value=123), \
             patch('builtins.print'), patch.dict(os.environ, {'TERM': 'xterm-kitty', 'REDUCE_MOTION': '0'}):
            with patch.object(bonsai, 'prepared_identity', return_value={'seed': 42}):
                bonsai.greeting(42, 2, 'informal', opening_shown=True)
        terminal.write.assert_not_called()

    def test_seedling_skips_invisible_mature_decoration_plans(self):
        with patch.object(bonsai, 'blossom_plan', side_effect=AssertionError('early flowers')), \
             patch.object(bonsai, 'knurl_sites', side_effect=AssertionError('early knots')), \
             patch.object(bonsai, 'trunk_scar', side_effect=AssertionError('early scar')):
            for day in (0, 7, 14):
                bonsai.specimen_canvas(day, 42)

    def test_single_launch_greeting_returns_worker_and_paints_terminal(self):
        import fcntl
        import pty
        import select
        import signal
        import struct
        import termios
        import time
        master, slave = pty.openpty()
        worker = None
        try:
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 1000, 800))
            result = subprocess.run(
                [str(SOURCE), '--greeting', '--seed', '42'],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=slave,
                env={**os.environ, 'TERM': 'xterm-256color', 'REDUCE_MOTION': '0',
                     'KITTY_WINDOW_ID': '1'},
                timeout=5, check=True)
            worker = int(result.stdout.strip())
            painted = b''
            deadline = time.monotonic() + 5
            while b'\x1b[?2026l' not in painted and time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    painted += os.read(master, 65536)
            self.assertIn(b'\x1b[H\x1b[26B', painted)
            self.assertIn(b'\x1b[?2026l', painted)
        finally:
            if worker is not None:
                os.kill(worker, signal.SIGTERM)
            os.close(slave)
            os.close(master)

    def test_single_launch_greeting_is_quiet_without_terminal(self):
        result = subprocess.run([str(SOURCE), '--greeting'], capture_output=True, check=True)
        self.assertEqual((result.stdout, result.stderr), (b'', b''))

    def test_redirected_greeting_is_quiet(self):
        result = subprocess.run([str(SOURCE)], capture_output=True, check=True)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(result.stderr, b'')


if __name__ == '__main__':
    unittest.main()
