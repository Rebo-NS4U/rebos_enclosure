"""Exercise wallpaper extraction and compare its accents to the real tree renderer."""
import json
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
                        for role, leaf in [('primary', 'leaf4'), ('secondary', 'leaf1'),
                                           ('tertiary', 'leaf7')]:
                            actual = '#' + ''.join(f'{int(v):02x}' for v in
                                                   re.findall(r'\d+', inks[leaf])[-3:])
                            # Re-reading an 8-bit accent can shift the hue by one channel.
                            for i in (1, 3, 5):
                                self.assertLessEqual(abs(int(p[role][i:i+2], 16)
                                                         - int(actual[i:i+2], 16)), 1)
                        accents.append(p['primary'])
            self.assertEqual(len(set(accents)), 3)


if __name__ == '__main__':
    unittest.main()
