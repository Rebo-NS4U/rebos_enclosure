"""Validate shared compositor corners, including square and changed themes."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts'
sys.path.insert(0, str(SCRIPTS))
from apply_desktop_palette import apply_niri_theme

class ThemeRadiusTests(unittest.TestCase):
    def test_generated_window_and_popup_corners_follow_theme(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            theme = home / '.config/enclosure/shell/config/theme.json'
            theme.parent.mkdir(parents=True)
            palette = dict(primary='#112233', secondary='#223344', outlineVariant='#334455')
            for value, expected in [(16,16), (0,0), (24,24), (100,40), ('bad',16)]:
                theme.write_text(json.dumps({'roundness':value}))
                apply_niri_theme(palette, home)
                css = (home / '.cache/rebos_shell/niri-colors.kdl').read_text()
                self.assertEqual(css.count(f'geometry-corner-radius {expected}\n'), 2)
                self.assertIn('clip-to-geometry true', css)
                self.assertIn('active-color "#112233"', css)
            theme.unlink()
            apply_niri_theme(palette, home)
            self.assertIn('geometry-corner-radius 16', (home / '.cache/rebos_shell/niri-colors.kdl').read_text())
