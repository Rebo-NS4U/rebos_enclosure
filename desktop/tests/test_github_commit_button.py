"""Exercise commit confirmation and submission through real QML controls."""
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
               upstream: "origin/main", branches: ["main"],
               all_changes: [{path: "one.txt", kind: "Modified"}], staged: ["one.txt"]})
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
      let section = fixture.find(projects, i => i.objectName === "github-files-section");
      section.expanded = true;
      tester.wait(100);
      projects.y -= section.mapToItem(fixture, 0, 0).y - 10;
      let checkbox = fixture.find(section, i => i.modelData && i.modelData.path === "one.txt");
      fixture.check(checkbox, "Changed file can be selected");
      tester.mouseClick(checkbox);
      let message = fixture.find(section, i => i.placeholderText === "Commit message");
      message.text = "Selected commit";
      let button = fixture.find(section, i => i.text === "Commit selected staged files…");
      fixture.check(button.enabled, "Commit is enabled for selected staged files");
      projects.y -= button.mapToItem(fixture, 0, 0).y - 200;
      tester.wait(100);
      tester.mouseClick(button);
      tester.wait(100);
      fixture.check(projects.feedback.includes("commit"), "Commit confirmation explains the commit action");
      let overlay = directProjects.Window.window.contentItem;
      let confirm = fixture.find(overlay, i => i.text === "Confirm commit");
      fixture.check(confirm && confirm.visible, "Commit confirmation is visible");
      projects.checking = true;
      tester.wait(30);
      fixture.check(!confirm.enabled, "Confirmation waits for an active status check instead of dropping the request");
      projects.checking = false;
      tester.wait(30);
      fixture.check(confirm.enabled, "Confirmation becomes available after the check");
      tester.mouseClick(confirm);
      tester.wait(350);
      console.log("COMMIT BUTTON TEST PASSED"); Qt.quit();
     } catch (error) { console.error(error); Qt.exit(1); }
    }
   }
  }
 }
}
'''


class CommitButtonTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell is required')
    def test_selected_commit_confirmation_and_submission(self):
        self.run_harness(HARNESS)

    def run_harness(self, harness, inspection_delay=0):
        with tempfile.TemporaryDirectory(prefix='github-commit-button-') as temporary:
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
                ' Path("commit-request.json").write_text(json.dumps(request))\n'
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
            self.assertIn('COMMIT BUTTON TEST PASSED', result.stdout + result.stderr)
            self.assertEqual(json.loads((root / 'commit-request.json').read_text()),
                             {'action': 'commit', 'path': '/example/project', 'files': ['one.txt'], 'message': 'Selected commit'})
