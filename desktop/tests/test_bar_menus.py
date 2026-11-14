"""Load the bar menu family and exercise shared keyboard navigation."""
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
import qs.config
import qs.modules.theme
import qs.modules.components
import qs.modules.bar.island
ShellRoot {
 FloatingWindow {
  visible: true; implicitWidth: 600; implicitHeight: 700
  Item { id: host; anchors.fill: parent }
  TestCase { id: tester; when: false }
  Timer { interval: 600; running: true; onTriggered: {
   try {
    Config.theme.shellStyle = "frosted";
    for (const name of ["Alerts", "Battery", "Bluetooth", "Calendar", "MediaCenter", "Mic", "Power", "Sound", "Stats", "Wallpaper", "Weather", "Wifi"]) {
     const component = Qt.createComponent("modules/bar/island/Island" + name + "Panel.qml");
     if (component.status !== Component.Ready) throw Error(name + ": " + component.errorString());
     const menu = component.createObject(host);
     if (!menu) throw Error("Could not create " + name);
     menu.width = menu.implicitWidth; menu.height = menu.implicitHeight;
     tester.wait(30);
     const back = tester.findChild(menu, "island-menu-back");
     if (!back) throw Error(name + " missing back action");
     let activated = false;
     menu.backRequested.connect(() => activated = true);
     back.forceActiveFocus(); tester.keyClick(Qt.Key_Space); tester.wait(10);
     if (!activated) throw Error(name + " back action inaccessible to keyboard");
     for (const radius of [0, 16]) {
      Config.theme.roundness = radius; tester.wait(250);
      if (back.background.radius !== radius) throw Error(name + " ignores corner preference");
     }
     menu.destroy(); tester.wait(10);
    }
    console.log("BAR MENUS PASSED"); Qt.quit();
   } catch(e) { console.error(e); Qt.exit(1); }
  } }
 }
}'''

class BarMenuTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
    def test_menu_loads_and_keyboard_back_action(self):
        with tempfile.TemporaryDirectory(prefix='enclosure-bar-menus-') as directory:
            root = Path(directory)
            for name in ('modules', 'config', 'assets'):
                (root / name).symlink_to(APP / name)
            (root / 'shell.qml').write_text(HARNESS)
            (root / 'runtime').mkdir(mode=0o700)
            env = dict(os.environ, HOME=directory, XDG_RUNTIME_DIR=str(root/'runtime'),
                       QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_QPA_PLATFORMTHEME='basic')
            for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                env.pop(key, None)
            for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
                env[key] = str(root / key)
            result = subprocess.run(['qs', '-p', directory, '--no-color'], env=env,
                                    text=True, capture_output=True, timeout=25)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('BAR MENUS PASSED', result.stdout + result.stderr)
