"""Click the full GitHub panel and exercise terminal startup outcomes."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

APP = Path(__file__).resolve().parents[1] / 'payload/home/.config/quickshell'
HARNESS = '''import QtQuick
import QtTest
import Quickshell
import qs.modules.widgets.dashboard.controls
ShellRoot {
 FloatingWindow {
  id: window; visible: true; implicitWidth: 1100; implicitHeight: 1000
  GithubPanel { id: panel; anchors.fill: parent }
  TestCase { id: tester; when: false }
  function find(item, name) {
   if (item.objectName === name) return item;
   for (let child of item.children || []) {
    let result = window.find(child, name); if (result) return result;
   }
   return null;
  }
  function check(ok, message) { if (!ok) throw new Error(message); }
  Timer {
   interval: 1200; running: true
   onTriggered: {
    try {
     let button = window.find(panel, "github-update-installed-button");
     let controls = window.find(panel, "github-project-controls");
     let feedback = window.find(panel, "github-update-feedback");
     window.check(button.enabled, "Update action is available");
     // Bring the button into view just as a user scrolling the panel would.
     for (let ancestor = button.parent; ancestor; ancestor = ancestor.parent) {
      if (ancestor.contentY !== undefined && ancestor.contentItem) {
       let point = button.mapToItem(ancestor.contentItem, 0, button.height / 2);
       ancestor.contentY = Math.max(0, point.y - ancestor.height / 2);
      }
     }
     tester.wait(30);
     tester.mouseClick(button);
     tester.wait(400);
     window.check(feedback.visible && feedback.text.length > 0, "Feedback is displayed beside the action");
     EXPECTATIONS
     console.log("UPDATE BUTTON PASSED"); Qt.quit();
    } catch (error) { console.error(error); Qt.exit(1); }
   }
  }
 }
}
'''


class UpdateButtonTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell is required')
    def test_terminal_outcomes(self):
        cases = {
            'open': ('#!/bin/sh\nsleep 3\n', '''
                window.check(!button.enabled && button.text.includes("open"), "Open window is indicated");
                window.check(feedback.text.includes("Switch to"), "Window switching guidance is visible");'''),
            'failure': ('#!/bin/sh\necho "terminal failed" >&2\nexit 7\n', '''
                window.check(button.enabled && controls.updateFailed, "Failed launch allows retry");
                window.check(feedback.text.includes("exit 7"), "Terminal exit failure is visible");'''),
            'missing': ('#!/nonexistent-enclosure-test-interpreter\n', '''
                window.check(button.enabled && controls.updateFailed, "Missing terminal allows retry");
                window.check(feedback.text.includes("Could not start"), "Startup failure is visible");'''),
        }
        for name, (terminal, expectations) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix='github-button-') as temporary:
                root = Path(temporary)
                for directory in ('modules', 'config', 'assets'):
                    shutil.copytree(APP / directory, root / directory)
                (root / 'scripts').mkdir()
                (root / 'scripts/github_projects.py').write_text(
                    'print(\'{"ok":true,"desktop_path":"/repo","projects":[],"message":"Ready"}\')\n')
                (root / 'bin').mkdir()
                kitty = root / 'bin/kitty'
                kitty.write_text(terminal)
                kitty.chmod(0o755)
                (root / 'runtime').mkdir(mode=0o700)
                (root / 'shell.qml').write_text(HARNESS.replace('EXPECTATIONS', expectations))
                env = dict(os.environ, HOME=temporary, XDG_RUNTIME_DIR=str(root / 'runtime'),
                           QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                           QT_QPA_PLATFORMTHEME='basic', PATH=str(root / 'bin') + ':' + os.environ['PATH'])
                for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                    env.pop(key, None)
                for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
                    env[key] = str(root / key)
                result = subprocess.run(['qs', '-p', temporary, '--no-color'], env=env,
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('UPDATE BUTTON PASSED', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
