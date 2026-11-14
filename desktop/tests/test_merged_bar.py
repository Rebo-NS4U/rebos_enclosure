"""Exercise merged bar geometry, circular controls and expanding panels offscreen."""
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
import qs.modules.bar.layouts
ShellRoot {
 FloatingWindow {
  visible: true; implicitWidth: 1920; implicitHeight: 1200
  Item { id: host; width: 1920; height: 1200 }
  TestCase { id: tester; when: false }
  Timer { interval: 600; running: true; onTriggered: {
   try {
    Config.animDuration = 0;
    Config.bar.pinned = true;
    for (const name of ["IslandBar", "DefaultBar"]) {
     const component = Qt.createComponent("modules/bar/layouts/" + name + ".qml");
     if (component.status !== Component.Ready) throw Error(component.errorString());
     const bar = component.createObject(host, {screen: Quickshell.screens[0]});
     if (!bar) throw Error("Could not create " + name);
     tester.wait(100);
     for (const size of [1920, 1280]) {
      host.width = size; tester.wait(50);
      if (bar.targetWidth !== size) throw Error(name + " does not span screen: " + bar.targetWidth + " / " + size + " mode=" + bar.currentMode + " width=" + bar.width + "");
      for (const id of ["bar-volume", "bar-brightness", "bar-battery"]) {
       const control = tester.findChild(bar, id);
       if (!control || !control.flat || control.width <= 0 || control.height <= 0)
        throw Error(name + " missing circular control " + id);
       const pos = control.mapToItem(bar, 0, 0);
       if (pos.x < 0 || pos.x + control.width > size) throw Error(id + " outside bar");
      }
      for (const mode of ["dashboard", "sound", "battery", "calendar", "apps"]) {
       bar.expand(mode); tester.wait(50);
       if (!bar.islandActive || bar.targetWidth > 540 || bar.targetHeight <= 36)
        throw Error(name + " failed to expand " + mode);
       bar.collapse(); tester.wait(50);
       if (bar.islandActive || bar.targetWidth !== size) throw Error("Failed to collapse");
      }
     }
     bar.destroy(); tester.wait(50);
    }
    console.log("MERGED BAR PASSED"); Qt.quit();
   } catch(e) { console.error(e); Qt.exit(1); }
  } }
 }
}'''

class MergedBarTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
    def test_merged_layout_and_panels(self):
        with tempfile.TemporaryDirectory(prefix='enclosure-merged-bar-') as directory:
            root = Path(directory)
            for name in ('modules', 'config', 'assets'):
                (root / name).symlink_to(APP / name)
            for path in APP.iterdir():
                if path.suffix in ('.qml', '.js') and path.name != 'shell.qml':
                    (root / path.name).symlink_to(path)
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
            self.assertIn('MERGED BAR PASSED', result.stdout + result.stderr)
