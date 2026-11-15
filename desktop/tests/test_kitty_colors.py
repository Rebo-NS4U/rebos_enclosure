"""Render the real QML generator and validate it with Kitty's own parser."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

APP = Path(__file__).resolve().parents[2] / 'system/apps/shell'

class KittyColorsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs') and shutil.which('kitty'), 'Requires Quickshell and Kitty')
    def test_alpha_palette_exports_valid_kitty_rgb(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['modules', 'config', 'assets']:
                (root/name).symlink_to(APP/name)
            (root/'runtime').mkdir(mode=0o700)
            (root/'shell.qml').write_text('''import QtQuick
import Quickshell
import qs.modules.theme
import qs.config
ShellRoot {
 KittyGenerator { id: generator }
 Timer { interval:100; running:true; onTriggered: {
  Config.theme.monoFont = "JetBrains Mono";
  Config.theme.monoFontSize = 18;
  const p = {};
  for (const role of ["overSurface","background","overPrimary","primary","surfaceContainerLow","outline","red","lightRed","green","lightGreen","yellow","lightYellow","lightBlue","magenta","lightMagenta","cyan","lightCyan","overSurfaceVariant","outlineVariant","error","surface","secondary","overSecondary","tertiary","overTertiary"]) p[role] = "#112233";
  p.background = "#262724"; p.outlineVariant = "#40e3e3dc"; p.opacity = 0.68;
  console.log("KITTY_CONFIG:" + JSON.stringify(generator.render(p)));
  for (const style of ["monolith", "blueprint", "terminal-hardware", "frosted", "colorful", "smoked-acrylic", "glass-console", "circuit-glass"]) {
   p.style = style;
   console.log("STYLE_CONFIG:" + JSON.stringify({style:style, config:generator.render(p)}));
  }
  Qt.quit();
 } }
}''')
            env = dict(os.environ, HOME=directory, XDG_RUNTIME_DIR=str(root/'runtime'), QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='basic')
            for key in ['WAYLAND_DISPLAY','DISPLAY','DBUS_SESSION_BUS_ADDRESS']: env.pop(key,None)
            result = subprocess.run(['qs','-p',str(root/'shell.qml')],text=True,capture_output=True,env=env,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            line = next(line for line in (result.stdout+result.stderr).splitlines() if 'KITTY_CONFIG:' in line)
            config = json.loads(line.split('KITTY_CONFIG:',1)[1])
            self.assertIn('inactive_border_color #555652',config)
            self.assertIn('background_opacity 0.68',config)
            self.assertIn('font_family JetBrains Mono\nfont_size 13.5\n',config)
            self.assertIn('active_border_color #112233',config)
            expected = {
                'smoked-acrylic': ('14 16', '1pt', 'beam', 'fade'),
                'glass-console': ('16 18', '2pt', 'block', 'powerline'),
                'circuit-glass': ('14 18', '2pt', 'underline', 'separator'),
                'monolith': ('16 20', '0pt', 'block', 'separator'),
                'blueprint': ('12 16', '1pt', 'underline', 'separator'),
                'terminal-hardware': ('14 18', '2pt', 'block', 'powerline'),
                'frosted': ('12 14', '0.5pt', 'beam', 'fade'),
                'colorful': ('10 14', '1pt', 'beam', 'slant'),
            }
            styles = [json.loads(line.split('STYLE_CONFIG:',1)[1]) for line in (result.stdout+result.stderr).splitlines() if 'STYLE_CONFIG:' in line]
            self.assertEqual({value['style'] for value in styles}, set(expected))
            for value in styles:
                with self.subTest(style=value['style']):
                    rendered = value['config']
                    padding, border, cursor, tabs = expected[value['style']]
                    for setting in (f'window_padding_width {padding}', f'window_border_width {border}', f'cursor_shape {cursor}', f'tab_bar_style {tabs}', 'dynamic_background_opacity yes', 'background_opacity 0.68', 'font_family JetBrains Mono', 'cursor #112233'):
                        self.assertIn(setting + '\n', rendered)
                    candidate = root / (value['style'] + '.conf')
                    candidate.write_text(rendered)
                    code = f'from kitty.config import load_config; bad=[]; load_config({str(candidate)!r}, accumulate_bad_lines=bad); assert not bad, repr(bad)'
                    parsed = subprocess.run(['kitty','+runpy',code],text=True,capture_output=True)
                    self.assertEqual(parsed.returncode,0,parsed.stdout+parsed.stderr)
            path = root/'kitty.conf';path.write_text(config)
            code = f'from kitty.config import load_config; bad=[]; load_config({str(path)!r}, accumulate_bad_lines=bad); assert not bad, repr(bad)'
            parsed = subprocess.run(['kitty','+runpy',code],text=True,capture_output=True)
            self.assertEqual(parsed.returncode,0,parsed.stdout+parsed.stderr)
