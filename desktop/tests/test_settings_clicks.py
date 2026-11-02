"""Exercise shared Settings click targets and keybind search in an isolated window."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'payload/home/.config/quickshell'

HARNESS = '''import QtQuick
import QtQuick.Layouts
import QtTest
import Quickshell
import qs.modules.widgets.dashboard.controls
ShellRoot {
 FloatingWindow {
  id: window; visible: true; implicitWidth: 1050; implicitHeight: 760
  Item {
   id: fixture
   anchors.fill: parent
   TestCase { id: tester; when: false }
   property int clicks: 0
   ColumnLayout {
    id: samples; width: 300
    SettingsButton { id: button; text: "Test action"; onClicked: parent.parent.clicks++ }
    SettingsSectionCard { id: card; text: "Section"; onClicked: parent.parent.clicks++ }
    PanelTitlebar { id: titlebar; title: "Test"; actions: [{tooltip: "Refresh", onClicked: function() { button.clicked(); }}] }
    GithubSection { id: section; title: "Branches"; actionsEnabled: false; SettingsButton { text: "Blocked action" } }
   }
   KeybindingsPanel { id: keys; x: 330; width: 700; height: 480 }
   function find(item, name) {
    if (item.objectName === name) return item;
    for (let child of item.children || []) { let found = fixture.find(child, name); if (found) return found; }
    return null;
   }
   function check(ok, message) { if (!ok) throw new Error(message); }
   Timer {
    interval: 1800; running: true
    onTriggered: {
     try {
      tester.mouseClick(button); fixture.check(button.parent.parent.clicks === 1, "Settings button click");
      tester.mouseClick(card); fixture.check(button.parent.parent.clicks === 2, "Section card click");
      let action = fixture.find(titlebar, "settings-titlebar-action-0");
      fixture.check(action && action.enabled && action.width > 0, "Titlebar action reachable");
      tester.mouseClick(action); fixture.check(button.parent.parent.clicks === 3, "Titlebar action click");
      let toggle = fixture.find(section, section.objectName + "-toggle");
      tester.mouseClick(toggle); fixture.check(section.expanded, "Disabled actions must not block section opening");
      keys.bindings = [{key:"Super+B", action:"Open browser", group:"Desktop"},
                       {key:"Super+T", action:"Open terminal", group:"Desktop"}];
      let input = fixture.find(keys, "shortcut-search-input");
      let search = fixture.find(keys, "shortcut-search-button");
      let clear = fixture.find(keys, "shortcut-search-clear");
      fixture.check(search.enabled && search.visible && search.height > 0, "Search button reachable");
      input.text = "browser";
      tester.mouseClick(search); fixture.check(keys.filteredBindings.length === 1 && input.inputActiveFocus, "Search filters and focuses");
      tester.mouseClick(clear); fixture.check(keys.filteredBindings.length === 2 && input.text === "", "Clear restores shortcuts");
      keys.height = 340;
      fixture.check(fixture.find(keys, "shortcut-add-open").enabled, "Add remains enabled on small windows");
      const panels = ["WifiPanel", "BluetoothPanel", "AudioMixerPanel", "ThemePanel", "SystemPanel",
                      "ShellPanel", "KeybindingsPanel", "WindowRulesPanel", "DisplayPanel", "GithubPanel"];
      for (let panel of panels) {
       let c = Qt.createComponent("modules/widgets/dashboard/controls/" + panel + ".qml");
       fixture.check(c.status === Component.Ready, panel + ": " + c.errorString());
      }
      let ai = Qt.createComponent("modules/widgets/config/AiPanel.qml");
      fixture.check(ai.status === Component.Ready, ai.errorString());
      keys.visible = false;
      samples.visible = false;
      for (let name of ["SystemPanel", "ShellPanel", "ThemePanel"]) {
       let component = Qt.createComponent("modules/widgets/dashboard/controls/" + name + ".qml");
       let page = component.createObject(fixture, {width: 1000, height: 740});
       fixture.check(page !== null, name + " instantiated");
       tester.wait(40);
       let cards = [];
       function collect(item) {
        if (item.objectName.startsWith("settings-section-")) cards.push(item);
        for (let child of item.children || []) collect(child);
       }
       collect(page);
       fixture.check(cards.length > 0, name + " has navigation cards");
       for (let target of cards) {
        page.currentSection = "";
        tester.wait(30);
        fixture.check(target.enabled && target.visible && target.width > 0 && target.height > 0, name + " card enabled");
        for (let ancestor = target.parent; ancestor; ancestor = ancestor.parent) {
         if (ancestor.contentY !== undefined && ancestor.contentItem && ancestor.contentHeight > ancestor.height) {
          let point = target.mapToItem(ancestor.contentItem, 0, target.height / 2);
          ancestor.contentY = Math.max(0, Math.min(ancestor.contentHeight - ancestor.height, point.y - ancestor.height / 2));
         }
        }
        tester.wait(20);
        tester.mouseClick(target);
        fixture.check(page.currentSection !== "", name + " section responds to click: " + target.objectName);
       }
       page.destroy();
       tester.wait(20);
      }
      console.log("SETTINGS CLICK TESTS PASSED"); Qt.quit();
     } catch (error) { console.error(error); Qt.exit(1); }
    }
   }
  }
 }
}
'''


class SettingsClickTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell is required')
    def test_controls_and_search(self):
        with tempfile.TemporaryDirectory(prefix='settings-clicks-') as temporary:
            root = Path(temporary)
            for name in ('modules', 'config', 'assets'):
                shutil.copytree(APP / name, root / name)
            (root / 'scripts').mkdir()
            (root / 'scripts/list_keybindings.py').write_text(
                'print(\'{"bindings": [], "files": [], "error": ""}\')\n')
            (root / 'shell.qml').write_text(HARNESS)
            (root / 'runtime').mkdir(mode=0o700)
            env = dict(os.environ, HOME=temporary, XDG_RUNTIME_DIR=str(root / 'runtime'),
                       QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_QPA_PLATFORMTHEME='basic')
            for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                env.pop(key, None)
            for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
                env[key] = str(root / key)
            result = subprocess.run(['qs', '-p', temporary, '--no-color'], env=env,
                                    capture_output=True, text=True, timeout=25)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('SETTINGS CLICK TESTS PASSED', output)

if __name__ == '__main__':
    unittest.main()
