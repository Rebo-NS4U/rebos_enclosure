import json
import re
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts'
sys.path.insert(0, str(SCRIPTS))
from standard_theme import apply, metrics, gtk_css, qt_css, browser_css
from apply_app_palette import read_jsonc

PALETTE = json.loads((SCRIPTS.parents[2] / 'cache-defaults/rebos_shell/effective-palette.json').read_text())


class StandardThemeTests(unittest.TestCase):
    def test_preserves_custom_css_qt_sheets_and_unrelated_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            gtk = home / '.config/gtk-3.0/gtk.css'
            gtk.parent.mkdir(parents=True)
            gtk.write_text('/* Personal rule */\n.my-widget { color: red; }\n')
            qt = home / '.config/qt6ct/qt6ct.conf'
            qt.parent.mkdir(parents=True)
            qt.write_text('[Interface]\nstylesheets=/tmp/personal.qss\nwheel_scroll_lines=7\n')
            apply(PALETTE, home)
            self.assertIn('.my-widget', gtk.read_text())
            self.assertEqual(gtk.read_text().count('@import'), 1)
            self.assertIn('/tmp/personal.qss', qt.read_text())
            self.assertIn('wheel_scroll_lines=7', qt.read_text())
            before = {f: f.read_bytes() for f in home.rglob('*') if f.is_file()}
            apply(PALETTE, home)
            self.assertEqual(before, {f: f.read_bytes() for f in home.rglob('*') if f.is_file()})

    def test_shared_metrics_follow_active_config_and_reject_css_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / '.config/enclosure/shell/config/theme.json'
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps({'font': 'JetBrains Mono', 'fontSize': 18, 'roundness': 9}))
            m = metrics(home)
            self.assertEqual((m['size'], m['radius']), (18, 9))
            self.assertIn('border-radius: 9px', qt_css(PALETTE, m))
            target.write_text(json.dumps({'font': 'bad"; color:red;', 'fontSize': 999, 'roundness': -2}))
            m = metrics(home)
            self.assertEqual((m['font'], m['size'], m['radius']), ('JetBrains Mono', 32, 0))

    def test_all_component_corners_share_metric(self):
        for radius in (0, 9, 16, 24):
            m = dict(font='JetBrains Mono', size=14, radius=radius)
            for css in (gtk_css(PALETTE, m)[1], qt_css(PALETTE, m), browser_css(PALETTE, m)):
                corners = set(map(int, re.findall(r'border-radius: (\d+)px', css)))
                self.assertIn(radius, corners)
                self.assertLessEqual(corners, {radius, 99})  # Circular controls.

    def test_vscode_custom_colors_and_comments_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            path = home / '.config/Code/User/settings.json'
            path.parent.mkdir(parents=True)
            path.write_text('// My setting\n{"editor.fontSize":17,"workbench.colorCustomizations":{"custom.test":"#123456"},}\n')
            apply(PALETTE, home)
            self.assertIn('// My setting', path.read_text())
            value = read_jsonc(path.read_text())
            self.assertEqual(value['editor.fontSize'], 17)
            self.assertEqual(value['workbench.colorCustomizations']['custom.test'], '#123456')
            self.assertEqual(value['workbench.colorCustomizations']['menu.selectionBackground'], PALETTE['surfaceContainerHigh'])

    def test_symlinks_and_permissions_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / 'user.css'
            target.write_text('/* User CSS */\n'); target.chmod(0o600)
            link = home / '.config/gtk-4.0/gtk.css'
            link.parent.mkdir(parents=True); link.symlink_to(target)
            apply(PALETTE, home)
            self.assertTrue(link.is_symlink())
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertIn('User CSS', target.read_text())


if __name__ == '__main__':
    unittest.main()
