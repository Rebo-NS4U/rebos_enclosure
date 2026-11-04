"""Exercise themed menu roles, keyboard selection and disabled actions offscreen."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

APP = Path(__file__).resolve().parents[2] / 'system/apps/shell'
HARNESS = '''import QtQuick
import QtTest
import Quickshell
import qs.modules.components
import qs.modules.widgets.dashboard.controls
import qs.modules.widgets.dashboard.wallpapers
ShellRoot {
 FloatingWindow {
  visible: true; implicitWidth: 600; implicitHeight: 500
  SettingsComboBox { id: combo; width: 240; model: [{label:"First",value:1},{label:"Second",value:2}]; textRole:"label"; valueRole:"value" }
  WallpaperChoice { id: wallpaper; y:80; width:240; model:[{label:"Wallpaper"}]; textRole:"label" }
  OptionsMenu { id: menu; items:[{text:"Action",onTriggered:()=>{}},{isSeparator:true},{text:"Disabled",enabled:false}] }
  TestCase { id: tester; when:false }
  Timer { interval:600; running:true; onTriggered: {
   try {
    combo.popup.open(); tester.wait(80);
    if (!combo.popup.visible || combo.currentValue !== 1) throw Error("Combo popup/value");
    combo.forceActiveFocus(); tester.keyClick(Qt.Key_Down); tester.keyClick(Qt.Key_Return); tester.wait(50);
    if (combo.currentValue !== 2) throw Error("Keyboard selection");
    combo.popup.close(); wallpaper.popup.open(); tester.wait(50);
    if (!wallpaper.popup.visible || wallpaper.displayText !== "Wallpaper") throw Error("Wallpaper role");
    wallpaper.popup.close(); menu.open(); tester.wait(50);
    if (!menu.visible || menu.itemAt(2).enabled) throw Error("Menu disabled state");
    menu.close(); console.log("MENU RUNTIME PASSED"); Qt.quit();
   } catch(e) { console.error(e); Qt.exit(1); }
  } }
 }
}'''

class MenuThemeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell is required')
    def test_menu_interactions(self):
        with tempfile.TemporaryDirectory(prefix='enclosure-menus-') as temporary:
            root = Path(temporary)
            for name in ('modules', 'config', 'assets'):
                shutil.copytree(APP / name, root / name)
            (root / 'shell.qml').write_text(HARNESS)
            (root / 'runtime').mkdir(mode=0o700)
            env = dict(os.environ, HOME=temporary, XDG_RUNTIME_DIR=str(root / 'runtime'),
                       QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_QPA_PLATFORMTHEME='basic')
            for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                env.pop(key, None)
            for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
                env[key] = str(root / key)
            result = subprocess.run(['qs', '-p', temporary, '--no-color'], env=env,
                                    capture_output=True, text=True, timeout=20, cwd=root)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('MENU RUNTIME PASSED', output)

if __name__ == '__main__':
    unittest.main()
