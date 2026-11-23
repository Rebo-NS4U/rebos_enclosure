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
    SettingsToggleRow { id: sharedToggle; label: "Shared toggle"; checked: true; onToggled: value => checked = value }
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
   function waitForLid(condition, message) {
    for (let attempt = 0; attempt < 60 && !condition(); attempt++) tester.wait(50);
    fixture.check(condition(), message);
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
      fixture.check(sharedToggle.checked, "Opening a standard toggle preserves the saved value");
      let toggleControl = fixture.find(sharedToggle, "settings-toggle-control");
      tester.mouseClick(toggleControl); fixture.check(!sharedToggle.checked, "Standard toggle saves a click");
      sharedToggle.checked = true; tester.wait(20);
      fixture.check(toggleControl.checked, "Standard toggle follows external changes");
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
      let displayComponent = Qt.createComponent("modules/widgets/dashboard/controls/DisplayPanel.qml");
      let desktop = displayComponent.createObject(fixture, {width: 700, height: 600});
      tester.wait(250);
      fixture.check(!fixture.find(desktop, "display-laptop-lid").visible, "Desktop hides lid controls");
      desktop.destroy();
      let laptop = displayComponent.createObject(fixture, {width: 700, height: 600});
      let lid = fixture.find(laptop, "display-laptop-lid");
      let lidChoice = fixture.find(lid, "display-lid-action");
      fixture.waitForLid(() => lid.visible && lidChoice.enabled, "Laptop exposes lid control");
      fixture.check(lidChoice.currentValue === "suspend", "Legacy suspend selection is restored");
      fixture.check(lidChoice.indexOfValue("hibernate") === -1, "Unsupported actions are hidden");
      for (let action of ["nothing", "lock", "suspend", "poweroff"]) {
       lidChoice.currentIndex = lidChoice.indexOfValue(action);
       lidChoice.activated(lidChoice.currentIndex);
       fixture.waitForLid(() => lidChoice.enabled && lidChoice.currentValue === action,
                          "Lid action can be set to " + action);
      }
      laptop.destroy();
      laptop = displayComponent.createObject(fixture, {width: 700, height: 600});
      lid = fixture.find(laptop, "display-laptop-lid");
      lidChoice = fixture.find(lid, "display-lid-action");
      fixture.waitForLid(() => lid.visible && lidChoice.currentValue === "poweroff",
                         "Lid action survives panel reopen");
      lidChoice.currentIndex = lidChoice.indexOfValue("default");
      lidChoice.activated(lidChoice.currentIndex);
      fixture.waitForLid(() => lidChoice.enabled && lidChoice.currentValue === "default",
                         "System default can be restored");
      laptop.destroy();
      for (let name of ["ShellPanel", "ThemePanel"]) {
       let component = Qt.createComponent("modules/widgets/dashboard/controls/" + name + ".qml");
       if (name === "ThemePanel") {
        Config.performance.desktopBlur = "light"; Config.performance.blurStrength = 50;
        Config.theme.shadowOpacity = 0.7; Config.theme.shadowBlur = 2;
        Config.theme.shadowXOffset = -5; Config.theme.shadowYOffset = 8;
       }
       let page = component.createObject(fixture, {width: 1000, height: 740});
       fixture.check(page !== null, name + " instantiated");
       tester.wait(40);
       let cards = [];
       function collect(item) {
        if (item.objectName.startsWith("settings-section-")) cards.push(item);
        for (let child of item.children || []) collect(child);
       }
       collect(page);
       fixture.check(cards.length === 0, name + " has no subsection navigation cards");
       let anchors = [];
       function collectSections(item) {
        if (item.settingsAnchor) anchors.push(item);
        for (const child of item.children || []) collectSections(child);
       }
       collectSections(page);
       fixture.check(anchors.length >= 6 && anchors.filter(item => item.visible).length >= 6, name + " controls share one scrollable page");
       if (name === "ShellPanel") {
        for (const sectionId of ["weather", "storage", "bar", "lockscreen", "system", "sidebar"]) {
         let group = fixture.find(page, "shell-group-" + sectionId);
         fixture.check(group && group.collapsible && !group.expanded && group.title.length > 0, "Shell group starts as a labeled dropdown: " + sectionId);
        }
        let bar = fixture.find(page, "shell-group-bar");
        let smallHeight = bar.implicitHeight;
        tester.mouseClick(fixture.find(bar, "shell-group-bar-expand")); tester.wait(40);
        fixture.check(bar.expanded && bar.implicitHeight > smallHeight + 100, "Shell dropdown expands inline");
        tester.mouseClick(fixture.find(bar, "shell-group-bar-expand")); tester.wait(40);
        fixture.check(!bar.expanded && bar.implicitHeight === smallHeight, "Shell dropdown collapses compactly");
        page.currentSection = "weather"; tester.wait(40);
        fixture.check(fixture.find(page, "shell-group-weather").expanded, "Weather search opens its dropdown");
       }
       if (name === "ThemePanel") {
        const advancedGrid = fixture.find(page, "theme-advanced-grid");
        fixture.check(advancedGrid.columns === 1, "Advanced theme options use a vertical accordion");
        let styleCards = [];
        function collectStyles(item) {
         if (item.objectName.startsWith("shell-style-")) styleCards.push(item);
         for (const child of item.children || []) collectStyles(child);
        }
        collectStyles(page);
        fixture.check(styleCards.length >= 3 && styleCards.every(card => card.height <= 120), "Theme previews stay compact");
        const shadows = fixture.find(page, "theme-group-shadow");
        fixture.check(shadows.collapsible && !shadows.expanded, "Advanced theme controls start collapsed");
        const collapsedHeight = shadows.implicitHeight;
        for (let ancestor = shadows.parent; ancestor; ancestor = ancestor.parent) {
         if (ancestor.contentY !== undefined && ancestor.contentItem) {
          ancestor.contentY = Math.max(0, shadows.mapToItem(ancestor.contentItem, 0, 0).y - 40);
         }
        }
        tester.wait(40);
        tester.mouseClick(fixture.find(shadows, "theme-group-shadow-expand")); tester.wait(40);
        fixture.check(shadows.expanded && shadows.implicitHeight > collapsedHeight + 100, "Advanced controls expand inline");
        tester.mouseClick(fixture.find(shadows, "theme-group-shadow-expand")); tester.wait(40);
        fixture.check(!shadows.expanded && shadows.implicitHeight === collapsedHeight, "Collapsing restores compact group height");
        page.currentSection = "shadow"; tester.wait(40);
        fixture.check(shadows.expanded, "Search opens the requested advanced controls");
        fixture.check(Config.theme.shadowOpacity === 0.7 && Config.theme.shadowBlur === 2 && Config.theme.shadowXOffset === -5 && Config.theme.shadowYOffset === 8, "Opening shadows preserves saved values");
        page.currentSection = "shadow"; tester.wait(30);
        let shadowOpacity = fixture.find(page, "shadow-opacity");
        shadowOpacity.value = 0.4; tester.wait(30);
        fixture.check(Config.theme.shadowOpacity === 0.4, "Shadow opacity saves");
        let shadow = fixture.find(page, "shadow-preview-shadow");
        fixture.check(shadow && shadow.visible && Math.abs(shadow.color.a - 0.4) < 0.01 && shadow.blur === 32, "Preview renders current shadow values");
        fixture.find(page, "shadow-x").value = 0.25; tester.wait(20);
        fixture.check(Config.theme.shadowXOffset === -10, "Shadow offset saves signed value");
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
      for (let style of ["frosted", "glass", "quiet", "colorful", "custom"]) {
       Config.theme.shellStyle = style;
       Config.theme.shellTransparency = 65;
       tester.wait(30);
       fixture.check(Math.abs(BarAppearance.panelOpacity(false) - 0.35) < 0.001, "Bar follows transparency for " + style);
       fixture.check(Math.abs(BarAppearance.panelOpacity(true) - 0.35) < 0.001, "Expanded bar follows transparency for " + style);
       fixture.check(BarAppearance.bordered && BarAppearance.panelBorder(false).toString() === Qt.alpha(Colors.primary, 0.5).toString(), "Bordered bar uses accent outline for " + style);
       fixture.check(BarAppearance.clockTint(false).a === 0 && BarAppearance.clockTint(true).a === 0, "Clock has no highlight for " + style);
       Config.theme.shellTransparency = -1;
       tester.wait(30);
       fixture.check(BarAppearance.opacity === Styling.getStyledRectConfig("bg").opacity, "Bar follows default theme opacity for " + style);
      }
      fixture.check(BarAppearance.workspaceTint(true, false).a > 0 && BarAppearance.workspaceTint(false, false).a === 0, "Bordered bar highlights the active workspace");
      for (let style of ["instrument", "frosted", "dithered", "quiet"]) {
       Config.theme.shellStyle = style;
       Config.bar.islandAppearance = "classic"; tester.wait(20);
       fixture.check(!BarAppearance.framed && BarAppearance.panelBorder(false).a === 0 && BarAppearance.clockTint(true).a === 0 && BarAppearance.workspaceTint(true, true).a === 0, "Plain bar has no outline or persistent accents in " + style);
      }
      Config.bar.islandAppearance = "glass";
      Config.theme.shellTransparency = 100; tester.wait(30);
      fixture.check(BarAppearance.opacity === 0, "Bar supports fully transparent theme");
      Config.theme.shellTransparency = 0; tester.wait(30);
      fixture.check(BarAppearance.opacity === 1, "Bar supports opaque theme");
      Config.theme.shellTransparency = -1;
      Config.theme.shellStyle = "glass";
      let fanWindowComponent = Qt.createComponent("modules/widgets/config/FanControlWindow.qml");
      fixture.check(fanWindowComponent.status === Component.Ready, fanWindowComponent.errorString());
      let dismissComponent = Qt.createComponent("modules/notifications/NotificationDismissButton.qml");
      fixture.check(dismissComponent.status === Component.Ready, dismissComponent.errorString());
      let criticalDismiss = dismissComponent.createObject(fixture, {urgency: 2});
      fixture.check(criticalDismiss.background.variant === "error" && criticalDismiss.contentItem.children.some(child => child.visible && child.text === criticalDismiss.glyph && child.color.toString() === Colors.overError.toString()), "Critical notification action uses readable error foreground");
      criticalDismiss.destroy();
      let themeButtonComponent = Qt.createComponent("modules/components/ThemeButton.qml");
      fixture.check(themeButtonComponent.status === Component.Ready, themeButtonComponent.errorString());
      let themedAction = themeButtonComponent.createObject(fixture, {text: "Action", width: 160, height: 36});
      fixture.check(themedAction !== null, "Themed action creates");
      themedAction.forceActiveFocus(); tester.wait(20);
      fixture.check(themedAction.background.border.width === 2, "Action shows keyboard focus");
      themedAction.enabled = false; tester.wait(20);
      fixture.check(themedAction.opacity < 1, "Disabled action is visibly distinct");
      themedAction.enabled = true;
      themedAction.highlighted = true; tester.wait(20);
      fixture.check(themedAction.background.variant === (themedAction.hovered ? "primaryfocus" : "primary"), "Highlighted action uses matching theme surface");
      themedAction.destroy();
      let sliderComponent = Qt.createComponent("modules/components/StyledSlider.qml");
      fixture.check(sliderComponent.status === Component.Ready, sliderComponent.errorString());
      let control = sliderComponent.createObject(fixture, {width: 300, height: 32, stepSize: 0.05, snapMode: "always"});
      tester.mouseClick(control, 150, 16); tester.wait(20);
      fixture.check(Math.abs(control.value - 0.5) < 0.01, "Slider click changes value");
      control.forceActiveFocus(); tester.keyClick(Qt.Key_Right);
      fixture.check(Math.abs(control.value - 0.55) < 0.01, "Slider keyboard uses configured step");
      tester.keyClick(Qt.Key_End); fixture.check(control.value === 1, "Slider End key reaches maximum");
      tester.keyClick(Qt.Key_Right); fixture.check(control.value === 1, "Slider clamps maximum");
      tester.keyClick(Qt.Key_Home); fixture.check(control.value === 0, "Slider Home key reaches minimum");
      control.updateOnRelease = true;
      tester.mousePress(control, 210, 16); tester.wait(20);
      fixture.check(control.value === 0 && control.isDragging, "Media seeking waits for release");
      tester.mouseRelease(control, 210, 16); tester.wait(20);
      fixture.check(Math.abs(control.value - 0.7) < 0.01 && !control.isDragging, "Media seeking commits on release");
      control.destroy();
      let weatherComponent = Qt.createComponent("modules/widgets/dashboard/controls/WeatherSettings.qml");
      fixture.check(weatherComponent.status === Component.Ready, weatherComponent.errorString());
      const savedUnit = Config.weather.unit;
      let weather = weatherComponent.createObject(fixture, {width: 360}); tester.wait(40);
      let unitLabel = fixture.find(weather, "weather-unit-label");
      let celsius = fixture.find(weather, "weather-unit-C");
      let fahrenheit = fixture.find(weather, "weather-unit-F");
      const labelBottom = unitLabel.mapToItem(weather, 0, unitLabel.height).y;
      fixture.check(labelBottom <= celsius.mapToItem(weather, 0, 0).y, "Temperature label is above its buttons");
      fixture.check(celsius.width >= celsius.contentItem.implicitWidth && fahrenheit.width >= fahrenheit.contentItem.implicitWidth, "Temperature button labels fit a narrow panel");
      fixture.check([celsius, fahrenheit].every(button => button.contentItem.children.some(child => child.visible && child.text === button.text && child.color.a > 0)), "Both temperature labels have visible theme colors");
      tester.mouseClick(fahrenheit); tester.wait(40); fixture.check(Config.weather.unit === "F" && fahrenheit.highlighted, "Fahrenheit button saves units");
      tester.mouseClick(celsius); tester.wait(40); fixture.check(Config.weather.unit === "C" && celsius.highlighted, "Celsius button saves units");
      Config.weather.unit = savedUnit; weather.destroy();
      let settingsComponent = Qt.createComponent("modules/widgets/dashboard/controls/SettingsTab.qml");
      fixture.check(settingsComponent.status === Component.Ready, settingsComponent.errorString());
      let settings = settingsComponent.createObject(fixture, {width: 1000, height: 740});
      fixture.check(settings !== null, "Grouped settings created");
      tester.wait(100);
      fixture.check(settings.filteredSections.length === 4, "Four sidebar categories");
      fixture.check([].concat.apply([], settings.categoryModel.map(group => group.sections)).sort((a,b) => a-b).join(",") === "0,1,2,3,4,6,7,8,9,10", "Every page belongs to exactly one category");
      fixture.check(settings.categoryModel[1].sections.join(",") === "9,7,8", "Desktop contains displays, input and window rules");
      let firstTab = fixture.find(settings, "settings-category-4");
      let nextTab = fixture.find(settings, "settings-category-9");
      fixture.check(firstTab && nextTab && nextTab.x > firstTab.x && nextTab.y === firstTab.y, "Main categories sit across the top");
      tester.mouseClick(nextTab); tester.wait(100);
      let shortcutsPage = fixture.find(settings, "settings-page-7");
      fixture.check(shortcutsPage && shortcutsPage.visible, "Category exposes page shortcuts");
      tester.mouseClick(shortcutsPage); tester.wait(100);
      fixture.check(settings.currentSection === 7, "Page shortcut opens keyboard settings");
      for (let legacy of [{sub: "weather", page: 6, target: "weather"}, {sub: "system", page: 6, target: "storage"}, {sub: "performance", page: 4, target: "performance"}]) {
       settings.openSection(5, legacy.sub);
       tester.tryVerify(() => {
        const activeLoader = fixture.find(settings, "settings-panel-" + legacy.page);
        return settings.currentSection === legacy.page && activeLoader?.item?.currentSection === legacy.target;
       }, 2000, "Old links open the relocated controls: " + legacy.sub);
      }
      for (let group of settings.categoryModel) {
       settings.openSection(group.section, "");
       tester.wait(60);
       fixture.check(settings.activeCategory.label === group.label, "Category activates");
       for (let section of group.sections) {
        settings.openSection(section, "");
        tester.tryVerify(() => {
         const panel = fixture.find(settings, "settings-panel-" + section);
         return panel?.visible && !!panel.item;
        }, 2000, "Category panel loads: " + section);
        fixture.check(settings.selectedIndex === settings.categoryModel.indexOf(group), "Category stays selected");
       }
      }
      GlobalStates.settingsCurrentTab = 8;
      tester.wait(60);
      fixture.check(settings.currentSection === 8 && settings.selectedIndex === 1, "External window-rule link selects Desktop");
      settings.searchQuery = "transparency";
      tester.tryVerify(() => settings.currentSection === 4 &&
       fixture.find(settings, "settings-panel-4")?.item?.currentSection === "blur", 2000,
       "Search opens the transparency controls");
      const loader = fixture.find(settings, "settings-panel-4");
      let categoryScroller = fixture.find(settings, "settings-category-scroll");
      let scrollingSlider = fixture.find(loader.item, "transparency-slider");
      tester.tryVerify(() => scrollingSlider.visible && scrollingSlider.width > 0 &&
       categoryScroller.contentHeight > categoryScroller.height, 2000, "Transparency slider is laid out");
      const sliderPoint = scrollingSlider.mapToItem(categoryScroller.contentItem, 0, 0);
      categoryScroller.contentY = Math.max(0, sliderPoint.y - 100);
      const previousValue = scrollingSlider.value;
      let beforeWheel = categoryScroller.contentY;
      tester.mouseWheel(scrollingSlider, scrollingSlider.width / 2, scrollingSlider.height / 2, 0, -120);
      tester.tryVerify(() => categoryScroller.contentY > beforeWheel, 2000, "Wheel over slider scrolls Settings");
      fixture.check(scrollingSlider.value === previousValue, "Wheel over slider preserves its value");
      const wheelSurface = fixture.find(settings, "settings-scroll-wheel");
      const scrollEnd = () => categoryScroller.contentHeight - categoryScroller.height;
      categoryScroller.contentY = scrollEnd();
      tester.tryVerify(() => Math.abs(categoryScroller.contentY - scrollEnd()) < 1,
       2000, "Settings is at the end of the page");
      beforeWheel = categoryScroller.contentY;
      tester.mouseWheel(wheelSurface, wheelSurface.width - 16, 80, 0, 120);
      tester.tryVerify(() => Math.abs(categoryScroller.contentY - Math.max(0, beforeWheel - 120)) < 1,
       2000, "Wheel reverses by 120 pixels from the end of Settings");
      settings.searchQuery = "";
      tester.wait(50);
      fixture.check(settings.currentSection === 4 && settings.selectedIndex === 0 && settings.filteredSections.length === 4, "Clearing search preserves page and category");
      settings.width = 850;
      settings.openSection(4, "colors"); tester.wait(150);
      fixture.check(!fixture.find(loader.item, "palette-open-palette"), "Color controls have no extra menu");
      let narrowWidth = loader.item.contentWidth;
      let paletteGrid = fixture.find(loader.item, "palette-sections");
      fixture.check(paletteGrid && paletteGrid.columns === 2, "Color tools use a compact grid in normal windows");
      settings.width = 1700; tester.wait(100);
      fixture.check(loader.item.contentWidth > narrowWidth + 500, "Loaded settings page expands with the window");
      fixture.check(paletteGrid.columns === 2, "Color sections use two columns in wide windows");
      settings.width = 600; tester.wait(100);
      // Preview cards must remain inside their grid after shrinking the window.
      let previewGrid = fixture.find(settings, "theme-preview-grid");
      for (let child of previewGrid.children) {
       if (!child.objectName.startsWith("shell-style-")) continue;
       fixture.check(child.x >= 0 && child.x + child.width <= previewGrid.width + 1, "Theme previews stay within the window");
       fixture.check(child.height >= child.implicitContentHeight + child.padding * 2, "Theme labels fit their cards");
      }
      fixture.check(paletteGrid.columns === 1 && loader.item.contentWidth < narrowWidth, "Color sections reflow when shrinking");
      fixture.check(!fixture.find(loader.item, "palette-navigation"), "No color subsection navigation");
      for (const pageId of ["picker", "presets", "apps", "palette"])
       fixture.check(fixture.find(loader.item, "palette-page-" + pageId).visible, "Color controls visible together: " + pageId);
      let scroll = fixture.find(settings, "settings-category-scroll");
      fixture.check(scroll.contentHeight > scroll.height, "Category scrolls through combined panels");
      settings.openSection(6, "bar"); tester.wait(150);
      let sharedGrid = fixture.find(settings, "theme-advanced-grid");
      let wallpaperColors = fixture.find(settings, "wallpaper-colors");
      fixture.check(wallpaperColors.title === "Wallpaper colors" && wallpaperColors.parent === sharedGrid, "Wallpaper colors joins the shared dropdown grid");
      for (const section of ["weather", "storage", "bar", "lockscreen", "system", "sidebar"]) {
       let group = fixture.find(settings, "shell-group-" + section);
       fixture.check(group.parent === sharedGrid && group.visible, "Shell dropdown joins Theme dropdowns: " + section);
      }
      let barGroup = fixture.find(settings, "shell-group-bar");
      fixture.check(settings.appearanceTab === "panels" && !barGroup.collapsible, "Shell links show direct panel controls");
      const expectedTabs = [
       {id: "style", anchors: []},
       {id: "colors", anchors: ["colors"]},
       {id: "wallpaper", anchors: ["wallpaper"]},
       {id: "typography", anchors: ["general"]},
       {id: "effects", anchors: ["performance", "motion", "blur", "shadow", "variants", "variants"]},
       {id: "panels", anchors: ["weather", "storage", "bar", "lockscreen", "system", "sidebar"]}
      ];
      for (const tab of expectedTabs) {
       const button = fixture.find(settings, "settings-theme-tab-" + tab.id);
       fixture.check(button && button.visible, "Theme section tab reachable: " + tab.id);
       tester.mouseClick(button); tester.wait(100);
       fixture.check(settings.appearanceTab === tab.id && button.highlighted, "Theme tab activates: " + tab.id);
       const groups = Array.from(sharedGrid.children).filter(child => child.visible && child.settingsAnchor);
       fixture.check(groups.map(child => child.settingsAnchor).sort().join(",") === tab.anchors.slice().sort().join(","), "Only selected tab controls appear: " + tab.id);
       fixture.check(groups.every(child => !child.collapsible), "Tab controls have visible headings without dropdowns");
      }
      settings.openSection(4, "motion"); tester.wait(100);
      fixture.check(settings.appearanceTab === "effects" && !barGroup.visible && fixture.find(settings, "theme-group-motion").visible, "Deep link activates Effects");
      settings.openSection(6, "bar"); tester.wait(100);
      fixture.check(scroll.contentY > 0, "Search links scroll to the target panel");
      settings.openSection(4, "blur"); tester.wait(200);
      let themePanel = fixture.find(settings, "settings-panel-4").item;
      let safeSlider = fixture.find(themePanel, "transparency-slider");
      let originalValue = safeSlider.value;
      let originalY = scroll.contentY;
      tester.mouseWheel(safeSlider, safeSlider.width / 2, safeSlider.height / 2, 0, -120); tester.wait(60);
      fixture.check(safeSlider.value === originalValue, "Wheel over slider must preserve value");
      fixture.check(scroll.contentY > originalY, "Wheel over slider scrolls settings");
      settings.openSection(4, "blur"); tester.wait(80);
      let combos = [];
      function findCombos(item) {
       if (item.popup !== undefined && item.currentIndex !== undefined) combos.push(item);
       for (let child of item.children || []) findCombos(child);
      }
      findCombos(themePanel);
      let combo = combos.find(item => item.visible && item.count > 1);
      fixture.check(combo !== undefined, "Settings dropdown available");
      let selected = combo.currentIndex;
      tester.mouseWheel(combo, 20, 20, 0, -120); tester.wait(40);
      fixture.check(combo.currentIndex === selected, "Wheel must preserve dropdown selection");
      let nestedList = Qt.createQmlObject('import QtQuick; ListView { width: 180; height: 120; clip: true; model: 20; delegate: Rectangle { width: 180; height: 40 } }', themePanel);
      nestedList.y = scroll.contentY + 20;
      tester.wait(40);
      let pageBeforeList = scroll.contentY;
      tester.mouseWheel(nestedList, 50, 50, 0, -120); tester.wait(40);
      fixture.check(nestedList.contentY > 0 && scroll.contentY === pageBeforeList, "Nested list scrolls while it has room");
      nestedList.contentY = nestedList.contentHeight - nestedList.height;
      tester.mouseWheel(nestedList, 50, 50, 0, -120); tester.wait(40);
      fixture.check(scroll.contentY > pageBeforeList, "List end hands wheel back to settings page");
      nestedList.destroy();
      settings.width = 1920; settings.height = 1080;
      settings.openSection(4, ""); tester.wait(100);
      fixture.check(settings.appearanceTab === "style", "Appearance opens the Style tab by default");
      fixture.check(fixture.find(settings, "theme-preview-grid").columns === 6, "Fullscreen theme previews fit in one row");
      fixture.check(scroll.contentHeight <= scroll.height, "Style page does not include hidden settings groups");
      const glyphCard = fixture.find(settings, "shell-style-glyph");
      fixture.check(glyphCard && glyphCard.visible, "Glyph is available in the style picker");
      const previousStyle = Config.theme.shellStyle;
      const previousTransparency = Config.theme.shellTransparency;
      const previousBlur = Config.performance.desktopBlur;
      tester.mouseClick(glyphCard); tester.wait(40);
      fixture.check(Styling.shellStyle === "glyph" && glyphCard.selected, "Clicking Glyph applies the theme");
      const glyphCanvas = fixture.find(glyphCard, "wallpaper-theme-canvas");
      fixture.check(glyphCanvas && glyphCanvas.finish === "glyph", "Glyph preview loads its dot matrix");
      fixture.check(glyphCard.previewPalette === null && glyphCard.sample.gradient[0][0] === Colors.background.toString(),
       "Glyph uses the current wallpaper background");
      Config.theme.shellStyle = previousStyle;
      Config.theme.shellTransparency = previousTransparency;
      Config.performance.desktopBlur = previousBlur;
      settings.openSection(6, "bar"); tester.wait(80);
      let fullscreenBar = fixture.find(settings, "shell-group-bar");
      fixture.check(!fullscreenBar.collapsible && fullscreenBar.visible && Math.abs(fullscreenBar.width - sharedGrid.width) < 1, "Panel controls use the available width");
      settings.width = 600; tester.wait(80);
      fixture.check(sharedGrid.columns === 1, "Narrow settings restores one readable column");
      settings.destroy();
      let windowComponent = Qt.createComponent("modules/widgets/config/SettingsWindow.qml");
      fixture.check(windowComponent.status === Component.Ready, windowComponent.errorString());
      GlobalStates.settingsWindowVisible = false;
      let settingsWindow = windowComponent.createObject(fixture);
      fixture.check(settingsWindow !== null, "Settings window created");
      let contentLoader = fixture.find(settingsWindow.contentItem, "settingsContentLoader");
      fixture.check(contentLoader && !contentLoader.active && !contentLoader.item, "Closed settings has no controls");
      GlobalStates.settingsWindowVisible = true;
      tester.wait(100);
      fixture.check(contentLoader.active && contentLoader.item, "Open settings creates controls");
      GlobalStates.settingsWindowVisible = false;
      tester.wait(50);
      fixture.check(!contentLoader.item, "Closing settings destroys controls");
      settingsWindow.destroy();
      console.log("SETTINGS CLICK TESTS PASSED"); Qt.quit();
     } catch (error) { console.error(error); Qt.exit(1); }
    }
   }
  }
 }
}
'''


class SettingsClickTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs') and shutil.which('niri'), 'Quickshell and Niri are required')
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
            for name in ('lid_settings.py', 'window_rules.py', 'list_keybindings.py'):
                shutil.copyfile(APP / 'scripts' / name, root / name)
            (root / 'scripts/lid_settings.py').write_text(
                'import json, sys\nfrom pathlib import Path\n'
                'root = Path(__file__).resolve().parents[1]\n'
                'sys.path.insert(0, str(root))\n'
                'import lid_settings\n'
                'lid_settings.is_available = lambda method: method in (None, "CanSuspend", "CanPowerOff")\n'
                'from lid_settings import settings\n'
                'probe = root / "probe"\n'
                'inputs = root / ("input-devices" if probe.exists() else "desktop-inputs")\n'
                'probe.touch()\n'
                'print(json.dumps(settings(sys.argv[1], root / "XDG_CONFIG_HOME", inputs)))\n')
            capability = root / 'input-devices/input0/capabilities'
            capability.mkdir(parents=True)
            (capability / 'sw').write_text('1\n')
            niri_config = root / 'XDG_CONFIG_HOME/niri/config.kdl'
            niri_config.parent.mkdir(parents=True)
            original_niri = '// Existing lid behavior\nswitch-events { lid-open { spawn "true"; }; }\n'
            fragment = root / 'XDG_CONFIG_HOME/quickshell/scripts/lid-suspend.kdl'
            fragment.parent.mkdir(parents=True)
            shutil.copyfile(APP / 'scripts/lid-suspend.kdl', fragment)
            shutil.copytree(APP / 'scripts/lid-actions', fragment.parent / 'lid-actions')
            niri_config.write_text(original_niri + f'include optional=true "{fragment}" // Enclosure lid suspend\n')
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
            self.assertEqual(niri_config.read_text(), original_niri)
            self.assertEqual(json.loads((root / 'review-request.json').read_text()),
                             {'action': 'review', 'path': '/example/selected-repository'})

if __name__ == '__main__':
    unittest.main()
