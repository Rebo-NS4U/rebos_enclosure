"""Exercise shared Settings click targets and keybind search in an isolated window."""
import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT.parent / 'system/apps/shell'

HARNESS = '''import QtQuick
import QtQuick.Layouts
import QtTest
import Quickshell
import qs.modules.widgets.dashboard.controls
import qs.config
import qs.modules.globals
import qs.modules.bar
import qs.modules.theme
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
   GithubPanel {
    id: github; visible: false; width: 700; height: 600; checkedAt: "test"
    result: ({status: "ahead", branch: "linux-desktop", default_branch: "main",
              ahead: 19, behind: 0, upstream: "origin/linux-desktop",
              upstream_ahead: 0, upstream_behind: 0})
   }
   GithubProjects {
    id: reviewControls; visible: false; width: 700; initialized: true
    selectedPath: "/example/selected-repository"
    project: ({path: "/example/selected-repository", upstream: "origin/main", upstream_ahead: 1,
               outgoing_commits: [{sha: "1234567890abcdef", title: "Selected repo work"}]})
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
      fixture.check(fixture.find(github, "github-default-branch-status").text === "Ahead of main", "Default comparison must name main");
      let comparison = fixture.find(github, "github-default-branch-counts");
      fixture.check(comparison.text.includes("linux-desktop vs main: 19 commits ahead"), "Ahead count names both branches");
      let pushStatus = fixture.find(github, "github-push-status");
      fixture.check(pushStatus.text.includes("No commits waiting to push to origin/linux-desktop"), "Already published branch must show no pending push");
      github.result = Object.assign({}, github.result, {upstream_ahead: 2});
      fixture.check(pushStatus.text.includes("2 commits waiting to push to origin/linux-desktop"), "Push count must use upstream, not default branch");
      fixture.check(comparison.text.includes("19 commits ahead"), "Default comparison remains separate");
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
       if (name === "ThemePanel") { Config.performance.desktopBlur = "light"; Config.performance.blurStrength = 50; }
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
       if (name === "ThemePanel") {
        fixture.check(Config.performance.desktopBlur === "medium" && Config.performance.blurStrength === 22, "Legacy lighter mode converts to shared scale: " + Config.performance.desktopBlur + "/" + Config.performance.blurStrength);
        page.currentSection = "blur";
        tester.wait(30);
        let transparency = fixture.find(page, "transparency-slider");
        let blur = fixture.find(page, "blur-strength-slider");
        fixture.check(transparency && blur && transparency.visible, "Glass sliders reachable");
        transparency.value = 0.65;
        fixture.check(Config.theme.shellTransparency === 65, "Transparency slider saves percentage");
        fixture.check(Math.abs(Styling.getStyledRectConfig("bg").opacity - 0.35) < 0.001, "Background opacity responds");
        fixture.check(Math.abs(Styling.getStyledRectConfig("popup").opacity - 0.35) < 0.001, "Popup opacity responds");
        Config.performance.desktopBlur = "shell";
        let lightPreset = fixture.find(page, "desktop-blur-light");
        let fullPreset = fixture.find(page, "desktop-blur-medium");
        lightPreset.clicked(); tester.wait(20);
        fixture.check(Config.performance.blurStrength === 22 && Math.abs(blur.value - 0.22) < 0.001, "Lighter preset moves strength slider");
        fixture.check(Config.performance.desktopBlur === "shell" && Config.theme.shellTransparency === 65, "Preset preserves scope and transparency");
        fixture.check(lightPreset.selected && !fullPreset.selected, "Lighter preset selected");
        fullPreset.clicked(); tester.wait(300);
        fixture.check(Config.performance.blurStrength === 50 && Math.abs(blur.value - 0.5) < 0.001 && fullPreset.selected, "Full preset moves slider and selection");
        blur.value = 0.8; tester.wait(20);
        fixture.check(Config.performance.blurStrength === 80, "Blur slider saves percentage");
        fixture.check(!lightPreset.selected && !fullPreset.selected && fixture.find(page, "blur-preset-status").text.includes("Custom"), "Slider changes mark custom strength");
        let scope = fixture.find(page, "blur-scope");
        scope.currentIndex = 0; scope.activated(0); tester.wait(20);
        fixture.check(Config.performance.desktopBlur === "medium" && Config.performance.blurStrength === 80, "Scope change preserves strength");
        Config.performance.desktopBlur = "off";
        tester.wait(20);
        fixture.check(!blur.enabled, "Blur strength disabled when off");
        fullPreset.clicked(); tester.wait(300);
        fixture.check(Config.performance.desktopBlur === "medium" && blur.enabled && fullPreset.selected, "Preset enables blur from off");
        fixture.find(page, "theme-transparency-reset").clicked(); tester.wait(20);
        fixture.check(Config.theme.shellTransparency === -1, "Theme transparency reset remains automatic");
       }
       page.destroy();
       tester.wait(20);
      }
      fixture.check(!fixture.find(github, "enclosure-development-open"), "Standalone development app removed");
      let review = fixture.find(reviewControls, "github-review-button");
      fixture.check(review && review.enabled, "Selected repository can be checked");
      let outgoing = fixture.find(reviewControls, "github-outgoing-section");
      fixture.check(outgoing.summary.includes("1 commit waiting for origin/main"), "Selected repo pending commits visible");
      reviewControls.checking = true;
      fixture.check(!review.enabled, "Review waits for project status");
      reviewControls.checking = false;
      review.clicked();
      tester.wait(350);
      fixture.check(reviewControls.failed, "Local check issues are highlighted");
      fixture.check(reviewControls.feedback.includes("staged whitespace"), "Local check report stays visible");
      reviewControls.selectedPath = "/example/another-repository";
      fixture.check(reviewControls.feedback === "", "Previous repo report cleared when selection changes");
      Config.bar.islandAppearance = "glass";
      Config.bar.islandOpacity = 20;
      Config.bar.islandAccent = 0;
      for (let style of ["glass", "quiet", "colorful", "dithered", "custom"]) {
       Config.theme.shellStyle = style;
       Config.theme.shellTransparency = 65;
       tester.wait(30);
       fixture.check(Math.abs(BarAppearance.panelOpacity(false) - 0.35) < 0.001, "Bar follows transparency for " + style);
       fixture.check(Math.abs(BarAppearance.panelOpacity(true) - 0.35) < 0.001, "Expanded bar follows transparency for " + style);
       fixture.check(BarAppearance.panelBorder(false).toString() === Config.resolveColor(Styling.getStyledRectConfig("bg").border[0]).toString(), "Bar border follows theme for " + style);
       fixture.check(BarAppearance.clockTint(false).r === BarAppearance.highlightColor.r, "Clock accent follows theme highlight for " + style);
       Config.theme.shellTransparency = -1;
       tester.wait(30);
       fixture.check(BarAppearance.opacity === Styling.getStyledRectConfig("bg").opacity, "Bar follows default theme opacity for " + style);
      }
      Config.theme.shellTransparency = 100; tester.wait(30);
      fixture.check(BarAppearance.opacity === 0, "Bar supports fully transparent theme");
      Config.theme.shellTransparency = 0; tester.wait(30);
      fixture.check(BarAppearance.opacity === 1, "Bar supports opaque theme");
      Config.theme.shellTransparency = -1;
      Config.theme.shellStyle = "glass";
      let settingsComponent = Qt.createComponent("modules/widgets/dashboard/controls/SettingsTab.qml");
      fixture.check(settingsComponent.status === Component.Ready, settingsComponent.errorString());
      let settings = settingsComponent.createObject(fixture, {width: 1000, height: 740});
      fixture.check(settings !== null, "Grouped settings created");
      tester.wait(100);
      fixture.check(settings.filteredSections.length === 5, "Five sidebar categories");
      fixture.check([].concat.apply([], settings.categoryModel.map(group => group.sections)).sort((a,b) => a-b).join(",") === "0,1,2,3,4,5,6,7,8,9,10", "Every page belongs to exactly one category");
      for (let group of settings.categoryModel) {
       settings.openSection(group.section, "");
       tester.wait(60);
       fixture.check(settings.activeCategory.label === group.label, "Category activates");
       for (let section of group.sections) {
        if (group.sections.length > 1) {
         let tab = fixture.find(settings, "settings-page-" + section);
         fixture.check(tab && tab.visible && tab.enabled, "Page tab reachable");
         tester.mouseClick(tab);
         tester.wait(60);
        }
        fixture.check(settings.currentSection === section, "Tab selects original page");
        fixture.check(settings.selectedIndex === settings.categoryModel.indexOf(group), "Category stays selected");
       }
      }
      GlobalStates.settingsCurrentTab = 8;
      tester.wait(60);
      fixture.check(settings.currentSection === 8 && settings.selectedIndex === 1, "External window-rule link selects Desktop");
      settings.searchQuery = "transparency";
      tester.wait(80);
      fixture.check(settings.currentSection === 4 , "Search opens appearance subsection");
      let loader = fixture.find(settings, "settings-panel-loader");
      tester.wait(150);
      fixture.check(loader.item && loader.item.currentSection === "blur", "Search loads transparency sliders directly");
      settings.searchQuery = "";
      tester.wait(50);
      fixture.check(settings.currentSection === 4 && settings.selectedIndex === 0 && settings.filteredSections.length === 5, "Clearing search preserves page and category");
      settings.destroy();
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
            (root / 'scripts/github_projects.py').write_text(
                'import sys,json\nfrom pathlib import Path\n'
                'data=json.loads(sys.stdin.readline())\n'
                'Path("review-request.json").write_text(json.dumps(data))\n'
                'print(json.dumps({"ok":True,"issues":True,"message":"Check found issues",'
                '"output":"staged whitespace", "refresh":False}))\n')
            (root / 'shell.qml').write_text(HARNESS)
            (root / 'runtime').mkdir(mode=0o700)
            env = dict(os.environ, HOME=temporary, XDG_RUNTIME_DIR=str(root / 'runtime'),
                       QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_QPA_PLATFORMTHEME='basic')
            for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                env.pop(key, None)
            for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
                env[key] = str(root / key)
            result = subprocess.run(['qs', '-p', temporary, '--no-color'], env=env,
                                    capture_output=True, text=True, timeout=25, cwd=root)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('SETTINGS CLICK TESTS PASSED', output)
            self.assertEqual(json.loads((root / 'review-request.json').read_text()),
                             {'action': 'review', 'path': '/example/selected-repository'})

if __name__ == '__main__':
    unittest.main()
