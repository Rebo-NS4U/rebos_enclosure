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
ShellRoot {
 KittyGenerator { id: generator }
 Timer { interval:100; running:true; onTriggered: {
  const p = {};
  for (const role of ["overSurface","background","overPrimary","primary","surfaceContainerLow","outline","red","lightRed","green","lightGreen","yellow","lightYellow","lightBlue","magenta","lightMagenta","cyan","lightCyan","overSurfaceVariant","outlineVariant","error","surface","secondary","overSecondary","tertiary","overTertiary"]) p[role] = "#112233";
  p.background = "#262724"; p.outlineVariant = "#40e3e3dc"; p.opacity = 0.68;
  console.log("KITTY_CONFIG:" + JSON.stringify(generator.render(p)));
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
            self.assertIn('active_border_color #112233',config)
            path = root/'kitty.conf';path.write_text(config)
            code = f'from kitty.config import load_config; bad=[]; load_config({str(path)!r}, accumulate_bad_lines=bad); assert not bad, repr(bad)'
            parsed = subprocess.run(['kitty','+runpy',code],text=True,capture_output=True)
            self.assertEqual(parsed.returncode,0,parsed.stdout+parsed.stderr)
