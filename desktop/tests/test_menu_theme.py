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
import qs.modules.theme
import qs.modules.bar
import qs.config
import qs.modules.components
import qs.modules.widgets.dashboard.controls
import qs.modules.widgets.dashboard.wallpapers
ShellRoot {
 FloatingWindow {
  visible: true; implicitWidth: 600; implicitHeight: 500
  StyledText { id: themedLabel; text:"Theme preview" }
  TestCase { id: typeTester; when:false }
  SettingsComboBox { id: combo; width: 240; model: [{label:"First",value:1},{label:"Second",value:2}]; textRole:"label"; valueRole:"value" }
  WallpaperChoice { id: wallpaper; y:80; width:240; model:[{label:"Wallpaper"}]; textRole:"label" }
  OptionsMenu { id: menu; items:[{text:"Action",onTriggered:()=>{}},{isSeparator:true},{text:"Disabled",enabled:false}] }
  TestCase { id: tester; when:false }
  Timer { interval:600; running:true; onTriggered: {
   try {
    Config.theme.shellStyle = "frosted"; Config.theme.shellTransparency = -1; tester.wait(30);
    if (Math.abs(BarAppearance.panelOpacity(false) - 0.68) > 0.001) throw Error("Frosted bar transparency");
    for (const radius of [0, 4, 12, 20]) {
     Config.theme.roundness = radius; tester.wait(250);
     for (const offset of [-12, 0, 4])
      if (Styling.radius(offset) !== radius) throw Error("Frosted radius setting ignored: " + radius);
     if (menu.menuRadius !== radius || combo.background.radius !== radius)
      throw Error("Menu/control radius did not follow setting: " + radius);
    }
    Config.theme.roundness = 4;
    if (Styling.getStyledRectConfig("bg").gradient.length !== 3) throw Error("Glass highlights missing");
    Config.theme.shellTransparency = 10; tester.wait(10);
    if (Math.abs(Styling.getStyledRectConfig("bg").opacity - 0.9) > 0.001) throw Error("Glass transparency override");
    Config.theme.shellTransparency = -1;
    Config.theme.shellStyle = "instrument"; tester.wait(30);
    if (!BarAppearance.framed || BarAppearance.panelOpacity(false) !== 1) throw Error("Instrument bar frame/opacity");
    if (BarAppearance.clockTint(false).a !== 1) throw Error("Instrument clock surface missing");
    if (BarAppearance.activeWorkspaceOutline !== Colors.primary) throw Error("Workspace accent missing");
    Config.theme.shellStyle = "quiet"; Config.bar.islandAppearance = "classic"; tester.wait(30);
    if (BarAppearance.instrument || BarAppearance.clockTint(false).a !== 0) throw Error("Classic bar style changed");
    Config.theme.shellStyle = "instrument";
    for (const offset of [-8, 0, 4, 12])
     if (Styling.radius(offset) !== Config.roundness) throw Error("Inconsistent shared radius");
    for (const child of menu.background.children)
     if (child.radius !== undefined && child.radius !== Config.roundness) throw Error("Menu corner radius");
    for (const size of [12, 18]) {
     Config.theme.fontSize = size; typeTester.wait(30);
     if (themedLabel.font.pixelSize !== size) throw Error("Text did not follow theme size");
     if (Styling.spacing(14) !== size) throw Error("Spacing did not follow type size");
    }
    Config.theme.fontSize = 13;
    Config.theme.roundness = 4;
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
