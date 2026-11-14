"""Exercise wallpaper extraction and compare its accents to the real tree renderer."""
import json
import colorsys
from pathlib import Path
import re
import runpy
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
SHELL = ROOT / 'system/apps/shell'


@unittest.skipUnless(shutil.which('matugen'), 'Matugen integration test')
class WallpaperLeafColors(unittest.TestCase):
    def test_wallpaper_changes_match_visible_tree(self):
        tree = runpy.run_path(str(ROOT / 'system/bin/bonsai-grow'))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            accents = []
            for name, rgb in [('red', (190, 45, 65)), ('blue', (40, 70, 200)),
                              ('neutral', (120, 120, 120))]:
                def chunk(kind, data):
                    return (struct.pack('>I', len(data)) + kind + data
                            + struct.pack('>I', zlib.crc32(kind + data)))
                image = folder / (name + '.png')
                image.write_bytes(b'\x89PNG\r\n\x1a\n'
                    + chunk(b'IHDR', struct.pack('>IIBBBBB', 8, 8, 8, 2, 0, 0, 0))
                    + chunk(b'IDAT', zlib.compress((b'\0' + bytes(rgb) * 8) * 8))
                    + chunk(b'IEND', b''))
                output = folder / 'colors.json'
                for mode in ('dark', 'light'):
                    subprocess.run(['bash', str(SHELL / 'scripts/generate_wallpaper_colors.sh'),
                        str(image), 'scheme-content', mode,
                        str(SHELL / 'assets/matugen/config.toml'), str(output)],
                        check=True, capture_output=True)
                    p = json.loads(output.read_text())
                    self.assertTrue(all(re.fullmatch('#[0-9a-fA-F]{6}', v) for v in p.values()))
                    if mode == 'dark':
                        inks = tree['specimen_palette'](42, [p[k] for k in
                                                              ('primary', 'secondary', 'tertiary')])
                        # The renderer preserves primary and borrows 6%/14% of
                        # secondary in linear light for neighboring clusters.
                        def linear(v):
                            return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
                        def srgb(v):
                            return 12.92 * v if v <= .0031308 else 1.055 * v ** (1 / 2.4) - .055
                        primary = [int(p['primary'][i:i+2], 16)/255 for i in (1, 3, 5)]
                        secondary = [int(p['secondary'][i:i+2], 16)/255 for i in (1, 3, 5)]
                        saturated = colorsys.rgb_to_hsv(*primary)[1] >= .08
                        for weight, leaf in [(0, 'leaf4'), (.06, 'leaf1'), (.14, 'leaf7')]:
                            weight = weight if saturated else 0
                            expected = [round(srgb(linear(a)*(1-weight) + linear(b)*weight)*255)
                                        for a, b in zip(primary, secondary)]
                            actual = [int(v) for v in re.findall(r'\d+', inks[leaf])[-3:]]
                            self.assertEqual(actual, expected)
                        accents.append(p['primary'])
            self.assertEqual(len(set(accents)), 3)

    def test_distinct_wallpaper_colors_and_contrast(self):
        def hsv(color):
            return colorsys.rgb_to_hsv(*(int(color[i:i+2], 16)/255 for i in (1, 3, 5)))
        def luminance(color):
            channels = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
            return sum(w * (v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4)
                       for w, v in zip((.2126, .7152, .0722), channels))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            def chunk(kind, data):
                return (struct.pack('>I', len(data)) + kind + data
                        + struct.pack('>I', zlib.crc32(kind + data)))
            # Large blue/gold regions, then a near-duplicate blue pair.
            for right, distinct in [((220, 160, 40), True), ((40, 170, 70), True),
                                    ((45, 85, 190), False)]:
                image = folder / 'pair.png'
                row = bytes((35, 80, 180))*32 + bytes(right)*32
                image.write_bytes(b'\x89PNG\r\n\x1a\n'
                    + chunk(b'IHDR', struct.pack('>IIBBBBB', 64, 64, 8, 2, 0, 0, 0))
                    + chunk(b'IDAT', zlib.compress((b'\0' + row)*64))
                    + chunk(b'IEND', b''))
                for mode in ('dark', 'light'):
                    output = folder / 'colors.json'
                    subprocess.run(['bash', str(SHELL/'scripts/generate_wallpaper_colors.sh'),
                        str(image), 'scheme-content', mode,
                        str(SHELL/'assets/matugen/config.toml'), str(output)],
                        check=True, capture_output=True)
                    p = json.loads(output.read_text())
                    h1, h2 = hsv(p['primary'])[0], hsv(p['secondary'])[0]
                    distance = min(abs(h1-h2), 1-abs(h1-h2))*360
                    if distinct:
                        self.assertGreater(distance, 35)
                        # Containers must follow the secondary, rather than the primary.
                        h3 = hsv(p['secondaryContainer'])[0]
                        self.assertLess(min(abs(h2-h3), 1-abs(h2-h3))*360, 20)
                    elif mode == 'dark':
                        self.assertLess(distance, 15)
                    for role in ('Primary', 'Secondary', 'Tertiary'):
                        a, b = sorted((luminance(p[role.lower()]), luminance(p['over'+role])))
                        self.assertGreaterEqual((b+.05)/(a+.05), 4.5)


if __name__ == '__main__':
    unittest.main()
