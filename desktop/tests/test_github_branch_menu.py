"""Click the actual branch dropdown in an isolated GitHub controls fixture."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

APP = Path(__file__).resolve().parents[2] / 'system/apps/shell'
HARNESS = '''import QtQuick
import QtQuick.Controls
import QtTest
import Quickshell
import qs.modules.widgets.dashboard.controls
ShellRoot {
 FloatingWindow {
  visible: true; implicitWidth: 800; implicitHeight: 600
  Item {
   id: fixture; anchors.fill: parent
   property bool copiedInstallation: false
   TestCase { id: tester; when: false }
   GithubProjects {
    id: directProjects; width: 760; initialized: true
    visible: !fixture.copiedInstallation
    selectedPath: "/example/project"
    project: ({path: "/example/project", local: "abc", branch: "main",
               upstream: "origin/main", branches: ["main", "feature/menu"]})
   }
   GithubPanel { id: installedPanel; anchors.fill: parent; visible: fixture.copiedInstallation }
   function find(item, predicate) {
    if (predicate(item)) return item;
    for (let child of item.children || []) {
     let found = find(child, predicate); if (found) return found;
    }
    return null;
   }
   function check(ok, message) { if (!ok) throw new Error(message); }
   Timer {
    interval: 500; running: true
    onTriggered: {
     try {
      let projects = fixture.copiedInstallation
          ? fixture.find(installedPanel, i => i.objectName === "github-project-controls") : directProjects;
      fixture.check(projects, "GitHub project controls exist");
      tester.tryVerify(() => projects.canEdit, 5000, "Default Enclosure selection resolves its local checkout");
      fixture.check(projects.canEdit, "Branch controls have a verified checkout");
      let section = fixture.find(projects, i => i.objectName === "github-branches-section");
      fixture.check(section, "Branch section exists");
      section.expanded = true;
      tester.wait(100);
      if (fixture.copiedInstallation) {
       let scroller = fixture.find(installedPanel, i => i.flickableDirection !== undefined);
       fixture.check(scroller, "GitHub panel scroll container exists");
       scroller.contentY = section.mapToItem(scroller.contentItem, 0, 0).y - 10;
      } else {
       projects.y -= section.mapToItem(fixture, 0, 0).y - 10;
      }
      tester.wait(100);
      let combo = fixture.find(section, i => i.popup !== undefined && i.currentText !== undefined);
      fixture.check(combo && combo.enabled && combo.count === 2, "Branch dropdown is enabled and populated");
      fixture.check(combo.width > 0 && combo.height > 0, "Branch dropdown has usable geometry");
      tester.mouseClick(combo);
      tester.wait(150);
      fixture.check(combo.popup.visible, "Click opens the branch dropdown");
      fixture.check(combo.popup.height > 0 && combo.popup.width > 0, "Branch popup has usable geometry");
      let option = combo.popup.contentItem.itemAtIndex(1);
      fixture.check(option && option.visible, "Second branch is visible");
      tester.mouseClick(option);
      tester.wait(150);
      fixture.check(combo.currentText === "feature/menu", "Click selects the requested branch");
      fixture.check(!combo.popup.visible, "Selecting a branch closes the popup");
      let button = fixture.find(section, i => i.text === "Switch to selected branch");
      fixture.check(button && button.enabled, "Switch button is available");
      tester.mouseClick(button);
      tester.wait(350);
      console.log("BRANCH MENU TEST PASSED"); Qt.quit();
     } catch (error) { console.error(error); Qt.exit(1); }
    }
   }
  }
 }
}
'''


class BranchMenuTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell is required')
    def test_click_selects_branch_and_sends_selected_name(self):
        self.run_harness(HARNESS)

    @unittest.skipUnless(shutil.which('qs'), 'Quickshell is required')
    def test_copied_desktop_selects_checkout_before_opening_branch_menu(self):
        for delay in (0, 0.4):
            with self.subTest(initial_inspection_delay=delay):
                self.run_harness(HARNESS.replace('property bool copiedInstallation: false',
                                                'property bool copiedInstallation: true'), delay)

    def run_harness(self, harness, inspection_delay=0):
        with tempfile.TemporaryDirectory(prefix='github-branch-menu-') as temporary:
            root = Path(temporary)
            for name in ('modules', 'config', 'assets'):
                shutil.copytree(APP / name, root / name)
            (root / 'scripts').mkdir()
            (root / 'scripts/github_projects.py').write_text(
                'import json,os,sys,time\nfrom pathlib import Path\n'
                'command=sys.argv[1]\n'
                'if command=="catalog":\n'
                ' print(json.dumps({"ok":True,"desktop_path":"/example/project","projects":[]}))\n'
                'elif command=="inspect":\n'
                ' if "--path" not in sys.argv: time.sleep(float(os.environ.get("BRANCH_TEST_INSPECTION_DELAY", "0")))\n'
                ' data={"status":"behind","local":"installed","default_branch":"main"}\n'
                ' if "--path" in sys.argv:\n'
                '  data.update(path=sys.argv[sys.argv.index("--path")+1],branch="main",upstream="origin/main",branches=["main","feature/menu"])\n'
                ' print(json.dumps(data))\n'
                'elif command=="action":\n'
                ' request=json.loads(sys.stdin.readline())\n'
                ' Path("branch-request.json").write_text(json.dumps(request))\n'
                ' print(json.dumps({"ok":True,"message":"Switch verified","refresh":False}))\n')
            (root / 'shell.qml').write_text(harness)
            (root / 'runtime').mkdir(mode=0o700)
            env = dict(os.environ, HOME=temporary, XDG_RUNTIME_DIR=str(root / 'runtime'),
                       BRANCH_TEST_INSPECTION_DELAY=str(inspection_delay),
                       QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_QPA_PLATFORMTHEME='basic')
            for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                env.pop(key, None)
            for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
                env[key] = str(root / key)
            result = subprocess.run(['qs', '-p', temporary, '--no-color'], env=env,
                                    capture_output=True, text=True, timeout=15, cwd=root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('BRANCH MENU TEST PASSED', result.stdout + result.stderr)
            self.assertEqual(json.loads((root / 'branch-request.json').read_text()),
                             {'action': 'switch', 'path': '/example/project', 'branch': 'feature/menu'})
