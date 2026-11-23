"""Exercise centered bar geometry, circular controls and expanding panels offscreen."""
import json
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
      if (bar.targetWidth <= 200 || bar.targetWidth >= size - 32)
       throw Error(name + " should stay compact: " + bar.targetWidth);
      const body = tester.findChild(bar, "typing-island-container");
      if (!body || Math.abs(body.x + body.width / 2 - size / 2) > 1)
       throw Error(name + " is not centered");
      for (const id of ["bar-volume", "bar-mic", "bar-battery"]) {
       const control = tester.findChild(bar, id);
       if (!control || !control.flat || control.width <= 0 || control.height <= 0)
        throw Error(name + " missing circular control " + id);
       const pos = control.mapToItem(bar, 0, 0);
       if (pos.x < body.x || pos.x + control.width > body.x + body.width) throw Error(id + " outside bar");
      }
      for (const mode of ["dashboard", "power", "sound", "mic", "wifi", "bluetooth", "alerts", "wallpapers", "battery", "weather", "media", "calendar", "apps"]) {
       const lazy = tester.findChild(bar, "island-lazy-" + mode);
       if (lazy && lazy.item) throw Error(mode + " eagerly loaded while closed");
       bar.expand(mode); tester.wait(50);
       if (lazy && (!lazy.active || !lazy.item)) throw Error(mode + " failed to load");
       const maxWidth = mode === "media" ? Math.min(Styling.spacing(620), size - 32) : 540;
       if (!bar.islandActive || bar.targetWidth > maxWidth || bar.targetHeight <= 36)
        throw Error(name + " failed to expand " + mode);
       bar.collapse(); tester.wait(50);
       if (lazy && (lazy.active || lazy.item)) throw Error(mode + " retained controls after close");
       if (bar.islandActive || (bar.targetWidth <= 200 || bar.targetWidth >= size - 32)) throw Error("Failed to collapse: " + bar.currentMode + " width=" + bar.targetWidth);
      }
     }
     bar.expand("stats"); tester.wait(50);
     if (bar.currentMode !== "collapsed") throw Error("Stats reopened the old embedded monitor");
     bar.destroy(); tester.wait(50);
    }
    console.log("MERGED BAR PASSED"); Qt.quit();
   } catch(e) { console.error(e); Qt.exit(1); }
  } }
 }
}'''

MOTION_HARNESS = '''import QtQuick
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
    Config.animDuration = 400;
    Config.bar.pinned = true;
    const component = Qt.createComponent('modules/bar/layouts/IslandBar.qml');
    if (component.status !== Component.Ready) throw Error(component.errorString());
    const bar = component.createObject(host, {screen: Quickshell.screens[0]});
    tester.wait(100);
    const body = tester.findChild(bar, 'typing-island-container');
    for (const name of ['bar-divider-volume-mic', 'bar-divider-mic-battery']) {
     const divider = tester.findChild(bar, name);
     if (divider) throw Error('Unexpected separator between meters: ' + name);
    }
    const power = tester.findChild(bar, 'island-lazy-power');
    const sound = tester.findChild(bar, 'island-lazy-sound');
    bar.expand('power'); tester.wait(70);
    if (!power.item || power.item.opacity <= 0 || power.item.opacity >= 1)
     throw Error('Incoming lazy panel must animate its first reveal');
    if (bar.revealProgress <= 0 || bar.revealProgress >= 1 || body.height < bar.islandHeight)
     throw Error('Opening silhouette must animate without collapsing to zero');
    tester.wait(500);
    bar.expand('sound'); tester.wait(60);
    if (!power.item || power.item.enabled || power.item.opacity <= 0 || power.item.opacity >= 1)
     throw Error('Outgoing panel must crossfade with input disabled');
    if (!sound.item || !sound.item.enabled || sound.item.opacity <= 0 || sound.item.opacity >= 1)
     throw Error('Incoming panel must overlap outgoing fade');
    bar.expand('wifi'); tester.wait(40);
    bar.expand('sound'); tester.wait(500);
    if (power.active || !sound.item || sound.item.opacity !== 1)
     throw Error('Rapid switching must release old loaders and settle current menu');
    bar.collapse(); tester.wait(60);
    if (bar.revealProgress <= 0 || bar.revealProgress >= 1)
     throw Error('Closing silhouette must animate');
    Config.animDuration = 0; tester.wait(100);
    if (bar.revealProgress !== 0 || bar.fadingModes.length || power.active || sound.active)
     throw Error('Reduced motion must release outgoing menus immediately');
    bar.expand('power'); tester.wait(40);
    if (bar.revealProgress !== 1 || !power.item || power.item.opacity !== 1)
     throw Error('Reduced motion must settle directly');
    bar.collapse(); tester.wait(40);
    if (bar.revealProgress !== 0 || power.active)
     throw Error('Reduced motion close must settle directly');
    console.log('MERGED BAR PASSED'); Qt.quit();
   } catch(e) { console.error(e); Qt.exit(1); }
  } }
 }
}
'''

class MergedBarTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
    def test_merged_layout_and_panels(self):
        self.run_harness(HARNESS)

    @unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
    def test_metropolis_finish_tracks_bar_expansion(self):
        harness = HARNESS.replace(
            "Config.animDuration = 0;",
            'tester.tryVerify(() => Config.themeReady); '
            'tester.compare(Config.theme.shellStyle, "metropolis"); Config.animDuration = 0;')
        harness = harness.replace(
            'const body = tester.findChild(bar, "typing-island-container");',
            """function findCompactFinish(node) {
       if (node.objectName === "wallpaper-theme-canvas" && node.barSurface) return node;
       for (const child of node.children || []) {
        const result = findCompactFinish(child);
        if (result) return result;
       }
       return null;
      }
      const finish = findCompactFinish(bar);
      if (!finish) throw Error("Missing collapsed city finish");
      const body = tester.findChild(bar, "typing-island-container");""")
        harness = harness.replace(
            "bar.expand(mode); tester.wait(50);",
            'bar.expand(mode); tester.wait(50); '
            'if (finish.barSurface) throw Error("Expanded panel retained compact city finish");')
        harness = harness.replace(
            "bar.collapse(); tester.wait(50);",
            'bar.collapse(); tester.wait(50); '
            'if (!finish.barSurface) throw Error("Collapsed bar lost city finish");')
        self.run_harness(harness, style="metropolis")

    @unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
    def test_menu_crossfade_interruptions_and_reduced_motion(self):
        self.run_harness(MOTION_HARNESS)

    def run_harness(self, harness, *, style=None):
        with tempfile.TemporaryDirectory(prefix='enclosure-merged-bar-') as directory:
            root = Path(directory)
            for name in ('modules', 'config', 'assets'):
                (root / name).symlink_to(APP / name)
            for path in APP.iterdir():
                if path.suffix in ('.qml', '.js') and path.name != 'shell.qml':
                    (root / path.name).symlink_to(path)
            (root / 'cli.sh').write_text('echo "$1" >> "$HOME/monitor-launches"\n')
            (root / 'shell.qml').write_text(harness)
            (root / 'runtime').mkdir(mode=0o700)
            env = dict(os.environ, HOME=directory, XDG_RUNTIME_DIR=str(root/'runtime'),
                       QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_QPA_PLATFORMTHEME='basic')
            for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                env.pop(key, None)
            for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
                env[key] = str(root / key)
            if style:
                config = Path(env['XDG_CONFIG_HOME']) / 'rebos_shell/config'
                config.mkdir(parents=True)
                theme = json.loads((APP / 'assets/presets/rebos_shell Default/theme.json').read_text())
                (config / 'theme.json').write_text(json.dumps(dict(theme, shellStyle=style)))
            result = subprocess.run(['qs', '-p', directory, '--no-color'], env=env,
                                    text=True, capture_output=True, timeout=25)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('MERGED BAR PASSED', result.stdout + result.stderr)
            if 'bar.expand("stats")' in harness:
                self.assertEqual((root / 'monitor-launches').read_text().splitlines(),
                                 ['compact-resources', 'compact-resources'])
