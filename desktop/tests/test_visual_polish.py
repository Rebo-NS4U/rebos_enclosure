"""Exercise repaired layouts, disclosure and controls with isolated QML state."""
import os
from pathlib import Path
import shutil
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def run_qml(app, harness, *, assistant=False):
    with tempfile.TemporaryDirectory(prefix='enclosure-polish-') as directory:
        root = Path(directory)
        for name in ('modules', 'config', 'assets'):
            if (app / name).exists():
                shutil.copytree(app / name, root / name)
        for path in app.iterdir():
            if path.suffix in ('.qml', '.js') and path.name != 'shell.qml':
                shutil.copyfile(path, root / path.name)
        if app.name == 'ui':
            # Keep real content and bindings; replace only native layer-window plumbing.
            # CI's offscreen Qt platform has no PanelWindow backend.
            for name in ('AnimeMenu.qml', 'PlaybackNextOverlay.qml'):
                path = root / name
                source = path.read_text().replace('PanelWindow {', 'FloatingWindow {')
                source = re.sub(r'(?m)^    mask: Region \{\n.*?^    \}\n', '', source, flags=re.S)
                source = '\n'.join(line for line in source.splitlines() if not any(
                    token in line for token in ('WlrLayershell.', 'exclusionMode:', 'mask: Region {', 'anchors { top:')))
                path.write_text(source)
        if assistant:
            # Exercise actual UI/session state without starting an agent or restoring accounts.
            state = root / 'modules/services/StateService.qml'
            state.write_text('''pragma Singleton
import Quickshell
Singleton {
 property bool initialized: true
 signal stateLoaded()
 function get(key, fallback) { return key === "assistantSessionChannels" ? [] : fallback; }
 function set(key, value) {}
}''')
            ai = root / 'modules/services/Ai.qml'
            ai.write_text(ai.read_text().replace('root.sessionEnabled = true;', 'root.sessionEnabled = false;'))
        (root / 'shell.qml').write_text(harness)
        (root / 'runtime').mkdir(mode=0o700)
        env = dict(os.environ, HOME=directory, XDG_RUNTIME_DIR=str(root / 'runtime'),
                   QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                   QT_QPA_PLATFORMTHEME='basic', NIRI_SOCKET='')
        for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
            env.pop(key, None)
        for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
            env[key] = str(root / key)
        result = subprocess.run(['qs', '-p', str(root), '--no-color'], env=env,
                                capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout + result.stderr


@unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
class VisualPolishTests(unittest.TestCase):
    def check_qml(self, app, scenario, **options):
        status, output = run_qml(ROOT / 'system/apps' / app, scenario, **options)
        self.assertEqual(status, 0, output[-7000:])
        self.assertIn('VISUAL POLISH PASSED', output)

    def test_wallpaper_gallery(self):
        self.check_qml('shell', '''import QtQuick
import QtTest
import Quickshell
import qs.modules.globals
import qs.modules.widgets.dashboard.controls
ShellRoot {
 FloatingWindow {
  visible: true; implicitWidth: 1024; implicitHeight: 760
  WallpaperSettings { id: page; width: 900 }
  QtObject {
   id: library
   readonly property string wallpaperDir: Quickshell.shellPath("assets/wallpapers_example")
   property var wallpaperPaths: Array.from({length: 10}, (_, i) =>
      wallpaperDir + "/rebos_shell-" + String(i + 1).padStart(2, "0") + ".png")
   property string currentWallpaper: wallpaperPaths[0]
   property var perScreenWallpapers: ({})
   readonly property var wallpaperModes: [{id:"auto",label:"Auto fit"}]
   readonly property string wallpaperMode: "auto"
   function getFileType(path) { return "image"; }
   function setWallpaper(path, screen) {
    if (screen) perScreenWallpapers = ({[screen]: path});
    else currentWallpaper = path;
   }
  }
  TestCase { id: test; when: false }
  Timer { interval: 100; running: true; onTriggered: {
   try {
    GlobalStates.wallpaperManager = library;
    GlobalStates.settingsWindowVisible = true;
    const grid = test.findChild(page, "wallpaper-gallery");
    test.tryVerify(() => grid.count === 10 && grid.itemAtIndex(1) !== null);
    if (grid.columns !== 3 || grid.cellWidth < 248) throw Error("Expected large previews");
    grid.screenName = "test-monitor";
    const second = grid.itemAtIndex(1);
    const preview = test.findChild(second, "wallpaper-preview");
    test.tryVerify(() => preview.status === Image.Ready && preview.width >= 230 && preview.height >= 120);
    test.mouseClick(second);
    if (!second.selected || library.currentWallpaper !== library.wallpaperPaths[1]
      || !GlobalStates.settingsWindowVisible) throw Error("Inline selection failed");
    library.perScreenWallpapers = ({"test-monitor":library.wallpaperPaths[0]});
    test.keyClick(Qt.Key_Right);
    test.keyClick(Qt.Key_Return);
    if (library.perScreenWallpapers["test-monitor"] !== library.wallpaperPaths[2]
      || library.currentWallpaper !== library.wallpaperPaths[1]) throw Error("Keyboard selection or monitor target failed");
    page.width = 400; test.wait(30);
    if (grid.columns !== 1 || grid.contentHeight <= grid.height) throw Error("Narrow gallery must reflow and scroll");
    library.wallpaperPaths = [];
    test.tryVerify(() => !grid.visible && grid.count === 0);
    console.log("VISUAL POLISH PASSED"); Qt.quit();
   } catch (error) { console.error(error); Qt.exit(1); }
  }}
 }
}''')

    def test_shadow_labels_and_moved_wallpaper_controls(self):
        self.check_qml('shell', '''import QtQuick
import QtTest
import Quickshell
import qs.config
import qs.modules.widgets.dashboard.controls
ShellRoot {
 FloatingWindow { visible:true; implicitWidth:1000; implicitHeight:850
  ThemePanel { id:page; width:460; height:780 }
  TestCase { id:test; when:false }
  Timer { interval:700; running:true; onTriggered:{
   try {
    Config.animDuration=0;
    for(let font of [14,18,24]) {
     Config.theme.fontSize=font; page.currentSection="shadow"; test.wait(80);
     let label=test.findChild(page,"shadow-blur-label");
     let slider=test.findChild(page,"shadow-blur");
     if(!label || label.paintedWidth>label.width+1)throw Error("Shadow label overflows at "+font);
     if(label.mapToItem(page,label.width,0).x>slider.mapToItem(page,0,0).x)throw Error("Shadow label covers slider");
    }
    Config.theme.fontSize=14; page.currentSection="general";test.wait(50);
    let folder=test.findChild(page,"wallpaper-folder");
    if(!folder || folder.visible)throw Error("Wallpaper control belongs outside Fonts and corners");
    page.currentSection="wallpaper";test.wait(50);
    if(!folder.visible)throw Error("Wallpaper folder must be reachable in Wallpaper");
    console.log("VISUAL POLISH PASSED");Qt.quit();
   }catch(e){console.error(e);Qt.exit(1);}
  }}
 }
}''')

    def test_assistant_alignment_compact_header_and_tool_disclosure(self):
        self.check_qml('assistant', '''import QtQuick
import QtTest
import Quickshell
import qs.config
import qs.modules.globals
import qs.modules.services
import qs.modules.sidebar
ShellRoot {
 FloatingWindow { visible:true;implicitWidth:1280;implicitHeight:1000
  Item { id:host;width:1200;height:950 }
  TestCase { id:test;when:false }
  Timer { interval:900;running:true;onTriggered:{
   try {
    Config.animDuration=0;
    Ai.addSession("default","codex");Ai.activeSession=Ai;
    Ai.currentChat=[{role:"assistant",content:"A readable answer."},
     {role:"assistant",content:"",functionCall:{name:"run_shell_command",args:{command:"echo private command details"}},functionApproved:true,toolStatus:"completed"}];
    GlobalStates.assistantScreenName=Quickshell.screens[0].name;
    GlobalStates.assistantVisible=true;
    let c=Qt.createComponent("modules/sidebar/AssistantSidebar.qml");
    if(c.status!==Component.Ready)throw Error(c.errorString());
    let sidebar=c.createObject(host,{targetScreen:Quickshell.screens[0],tiled:true});
    test.wait(350);
    const draft=test.findChild(sidebar,"assistantDraft");
    if(!draft)throw Error("Missing composer draft");
    draft.text="A draft message";
    for(let width of [1200,440]) {
     host.width=width;test.wait(250);
     let composer=test.findChild(sidebar,"assistantComposer");
     let messages=test.findChild(sidebar,"assistantConversation");
     let selectors=test.findChild(sidebar,"assistantSelectors");
     const tabStrip=test.findChild(sidebar,"assistantSessionTabs");
     const selectedTab=tabStrip.children.find(item => item.selected === true);
     if (!selectedTab || selectedTab.background.border.width <= 0
         || selectedTab.background.height - 2 * selectedTab.background.radius < 2)
      throw Error("Selected chat tab must keep a straight edge between its rounded corners");
     if(!composer||!messages||Math.abs(composer.width-messages.width)>1)throw Error("Composer and conversation must share width");
     if(composer.width>1000||composer.width>width||composer.width<width-80&&width<1000)throw Error("Responsive composer size");
     const typing=test.findChild(composer,"assistantTypingArea");
     const actions=test.findChild(composer,"assistantComposerActions");
     if(!typing || !actions || typing.width !== actions.width || typing.width !== composer.width - 32)
      throw Error("Typing box and action row must span the composer");
     if(typing.mapToItem(composer,0,typing.height).y > actions.mapToItem(composer,0,0).y
        || actions.mapToItem(composer,0,actions.height).y > composer.height)
      throw Error("Composer actions must fit below the typing box");
     if(selectors.columns!==(width>640?2:1))throw Error("Header must adapt to available width");
    }
    let button=test.findChild(sidebar,"assistantToolDetails_1");
    let command=test.findChild(sidebar,"assistantToolCommand_1");
    if(!button||!command||command.visible)throw Error("Completed commands must start collapsed");
    button.clicked();test.wait(50);
    if(!command.visible||!command.text.includes("private command details"))throw Error("Details must disclose the original command");
    Ai.currentChat=[{role:"assistant",content:"",functionCall:{name:"run_shell_command",args:{command:"echo approval details"}},functionPending:true}];
    test.wait(100);command=test.findChild(sidebar,"assistantToolCommand_0");
    if(!command||!command.visible)throw Error("Pending approvals must retain visible command details");
    Ai.currentChat=[];
    const greeting=test.findChild(sidebar,"assistantWelcomeMessage");
    if(!greeting)throw Error("Missing welcome message");
    greeting.parent.username="W".repeat(24);
    host.width=440;test.wait(150);
    if(!greeting.visible || !greeting.truncated || greeting.lineCount !== 1)
     throw Error("Long welcome messages must elide on one line");
    host.width=1200;test.wait(150);
    if(greeting.truncated)
     throw Error("Welcome messages must display in full when they fit");
    console.log("VISUAL POLISH PASSED");Qt.quit();
   }catch(e){console.error(e);Qt.exit(1);}
  }}
 }
}''', assistant=True)

    def test_assistant_slider_thumb_anchors_the_wave(self):
        self.check_qml('assistant', '''import QtQuick
import QtTest
import Quickshell
import qs.modules.components
ShellRoot {
 FloatingWindow { visible: true; implicitWidth: 320; implicitHeight: 140
  StyledSlider { id: horizontal; width: 160; height: 32 }
  StyledSlider { id: vertical; x: 200; width: 32; height: 120; vertical: true }
  TestCase { id: test; when: false }
  Timer { interval: 600; running: true; onTriggered: {
   try {
    for (const slider of [horizontal, vertical]) {
     test.mousePress(slider, slider.width / 2, slider.height / 2);
     test.wait(220);
     const layout = slider.children[slider.vertical ? 1 : 0];
     const [thumb, rail] = layout.children[0].children;
     const center = thumb.mapToItem(rail, thumb.width / 2, thumb.height / 2);
     const aligned = rail.children.some(item => item.wave === 0
      && Math.abs(item.x + item.width / 2 - center.x) <= rail.pitch * 0.75
      && Math.abs(item.y + item.height / 2 - center.y) < 0.01);
     if (!slider.isDragging || rail.energy < 0.5
         || Math.abs(center.x - rail.filledLength) > 0.01
         || Math.abs(center.y - rail.height / 2) > 0.01 || !aligned)
      throw Error("Assistant slider thumb must anchor the moving track during a drag");
     test.mouseRelease(slider, slider.width / 2, slider.height / 2);
    }
    console.log("VISUAL POLISH PASSED"); Qt.quit();
   } catch (error) { console.error(error); Qt.exit(1); }
  }}
 }
}''', assistant=True)

    def test_media_controls_keyboard_and_themed_sheet(self):
        self.check_qml('media/ui', '''import QtQuick
import QtTest
import Quickshell
import qs.modules.components
ShellRoot {
 FloatingWindow { visible:true;implicitWidth:600;implicitHeight:500
  MediaCheckBox { id:check;width:460;text:"An accessible setting with a long descriptive label" }
  MediaSlider { id:volume;y:100;width:460;from:5;to:100;stepSize:5;value:80 }
  MediaSlider { id:delay;y:160;width:460;from:-10;to:10;stepSize:0.1;value:0 }
  TestCase { id:test;when:false }
  Timer { interval:600;running:true;onTriggered:{
   try {
    check.forceActiveFocus();test.keyClick(Qt.Key_Space);
    if(!check.checked)throw Error("Checkbox keyboard toggle");
    check.enabled=false;test.keyClick(Qt.Key_Space);
    if(!check.checked)throw Error("Disabled checkbox changed");
    volume.forceActiveFocus();test.keyClick(Qt.Key_Right);
    if(volume.value!==85)throw Error("Volume units or keyboard step changed");
    delay.forceActiveFocus();test.keyClick(Qt.Key_Left);
    if(Math.abs(delay.value+0.1)>0.001)throw Error("Caption timing units changed");
    for (const slider of [volume, delay]) {
     const rail = slider.background.children[0];
     test.mousePress(slider, slider.width / 2, slider.height / 2);
     test.wait(220);
     const thumb = slider.handle;
     const center = thumb.mapToItem(rail, thumb.width / 2, thumb.height / 2);
     const aligned = rail.children.some(item => item.wave === 0
      && Math.abs(item.x + item.width / 2 - center.x) <= rail.pitch * 0.75
      && Math.abs(item.y + item.height / 2 - center.y) < 0.01);
     if (!slider.pressed || rail.energy < 0.5
         || Math.abs(center.x - rail.filledLength) > 0.01
         || Math.abs(center.y - rail.height / 2) > 0.01 || !aligned)
      throw Error("Media slider thumb must anchor the moving track during a drag");
     test.mouseRelease(slider, slider.width / 2, slider.height / 2);
    }
    const menu=Qt.createQmlObject(`import QtQuick; import "."; AnimeMenu {
      property var lastCommand: ({})
      function send(data): void { lastCommand=data }
    }`,check,"testMediaMenu");test.wait(50);
    let sheet=test.findChild(menu,"media-content-sheet");
    if(!sheet||sheet.styleOverride!==""||sheet.backgroundOpacity!==-1||sheet.variant!=="popup"
       ||sheet.rectOpacity!==sheet.variantConfig.opacity)throw Error("Content sheet must follow the selected popup theme");
    menu.receive(JSON.stringify({event:"ready",settings:{}}));
    test.tryVerify(()=>menu.ready);
    menu.implicitWidth=900;menu.implicitHeight=760;menu.opened=true;menu.pageView="settings";menu.settingsSection="subtitles";
    const settingsRow=test.findChild(menu,"whisper-mode-settings");
    const picker=row=>row.children.find(item=>item.modes!==undefined);
    if(!settingsRow.visible || picker(settingsRow).currentIndex!==0)
     throw Error("Missing audio setting must display Auto");
    picker(settingsRow).activated(1);
    if(menu.inFlightSettings.caption_language!=="en")throw Error("English choice must save en");
    menu.receive(JSON.stringify({event:"settings",request:menu.settingsInFlight,data:{caption_language:"en"}}));
    test.tryVerify(()=>!menu.settingsInFlight);
    menu.playback="Playing";menu.pageView="browse";
    const tracks=[{id:"off",label:"Off"},{id:"whisper",label:"Whisper English · local AI"},
                  {id:"native:3",label:"Video English · dialogue"}];
    menu.subtitleTracks={available:true,selected:"native:3",options:tracks};
    const button=test.findChild(menu,"playback-subtitles-button");
    const panel=test.findChild(menu,"playback-subtitles-panel");
    if(!button.enabled || !button.text.includes("dialogue"))throw Error("Footer must name the active track");
    test.mouseClick(button);test.tryVerify(()=>panel.opened);
    const playbackRow=test.findChild(panel.contentItem,"whisper-mode-playback");
    const sources=test.findChild(panel.contentItem,"playback-subtitle-sources");
    test.tryVerify(()=>sources.count===3 && sources.currentItem.selected);
    if(playbackRow.visible)throw Error("Video tracks must hide the Whisper settings");
    test.tryVerify(()=>sources.itemAtIndex(1)!==null);
    test.mouseClick(sources.itemAtIndex(1));
    if(menu.lastCommand.action!=="subtitle_source" || menu.lastCommand.source!=="whisper")
     throw Error("Choosing Whisper must request that source");
    menu.receive(JSON.stringify({event:"subtitle-tracks",selected:"whisper",options:tracks,available:true}));
    test.tryVerify(()=>playbackRow.visible && button.text.includes("Whisper · English"));
    if(!playbackRow.visible || picker(playbackRow).currentIndex!==1)
     throw Error("Playing Whisper must show the saved English mode");
    const modes=picker(playbackRow);
    test.mouseClick(modes);
    test.tryVerify(()=>modes.popup.opened && modes.popup.contentItem.itemAtIndex(2)!==null);
    test.mouseClick(modes.popup.contentItem.itemAtIndex(2));
    if(menu.inFlightSettings.caption_language!=="es")throw Error("Spanish choice must save es");
    menu.receive(JSON.stringify({event:"settings",request:menu.settingsInFlight,data:{caption_language:"es"}}));
    test.tryVerify(()=>!menu.settingsInFlight);
    if(picker(settingsRow).currentIndex!==2)throw Error("Saved Spanish mode must remain selected");
    picker(playbackRow).activated(0);
    if(menu.inFlightSettings.caption_language!=="auto")throw Error("Auto choice must save auto");
    menu.subtitleTracks={available:true,selected:"off",options:tracks};
    if(playbackRow.visible)throw Error("Whisper picker visible with subtitles off");
    menu.subtitleTracks={available:false,selected:"off",options:[]};
    test.tryVerify(()=>!panel.visible && !button.enabled);
    menu.destroy();console.log("VISUAL POLISH PASSED");Qt.quit();
   }catch(e){console.error(e);Qt.exit(1);}
  }}
 }
}''')


class ActivityTextTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node required')
    def test_markdown_is_removed_without_damaging_plain_identifiers(self):
        for app in ('assistant', 'shell'):
            source = (ROOT / f'system/apps/{app}/modules/services/AiSession.qml').read_text()
            start = source.index('    function activityText(text) {')
            function = source[start:source.index('\n    }', start) + 6]
            script = function + '''
const assert=require('node:assert/strict');
assert.equal(activityText('**Checking screenshot permission**'),'Checking screenshot permission');
assert.equal(activityText('## __Check__ *layout* and `caption_delay`'),'Check layout and caption_delay');
assert.equal(activityText('**Inspect `caption_delay`**'),'Inspect caption_delay');
assert.equal(activityText('[Review](https://example.com) ~~old~~ text'),'Review old text');
assert.equal(activityText('Keep foo_bar and 2 * 3'),'Keep foo_bar and 2 * 3');
'''
            result = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, app + ': ' + result.stderr)
