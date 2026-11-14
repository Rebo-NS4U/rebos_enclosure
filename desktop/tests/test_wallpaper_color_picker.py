"""Exercise pixel picking and explicit Matugen sources without touching the desktop."""
import colorsys
import json
import os
import runpy
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[2]
SHELL = Path(os.environ.get('REBOS_SHELL_TEST_APP', str(ROOT / 'system/apps/shell')))
GENERATOR = SHELL / 'scripts/generate_wallpaper_colors.sh'
CONFIG = SHELL / 'assets/matugen/config.toml'


def image(path):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    row = bytes((210, 30, 40)) * 32 + bytes((30, 60, 210)) * 32
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 64, 32, 8, 2, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress((b'\0' + row) * 32)) + chunk(b'IEND', b''))


def hue(color):
    return colorsys.rgb_to_hsv(*(int(color[i:i+2], 16) / 255 for i in (1, 3, 5)))[0]


@unittest.skipUnless(shutil.which('matugen'), 'Matugen required')
class PickedPaletteTests(unittest.TestCase):
    def test_picked_sources_in_dark_and_light_and_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            wallpaper = folder / 'wall paper #1.png'
            image(wallpaper)
            output = folder / 'colors.json'
            command = ['bash', str(GENERATOR), str(wallpaper), 'scheme-content', 'dark', str(CONFIG), str(output)]
            subprocess.run(command, check=True, capture_output=True)
            automatic = output.read_bytes()
            for mode in ('dark', 'light'):
                command[4] = mode
                for first, second in (('#31bd75', '#bd31af'), ('', '#bd31af'), ('#31bd75', '')):
                    subprocess.run(command + [first, second], check=True, capture_output=True)
                    palette = json.loads(output.read_text())
                    if mode == 'dark':
                        cache = folder / 'cache'
                        (cache / 'rebos_shell').mkdir(parents=True, exist_ok=True)
                        (cache / 'rebos_shell/effective-palette.json').write_text(json.dumps(palette))
                        with patch.dict(os.environ, {'XDG_CACHE_HOME': str(cache)}):
                            tree = runpy.run_path(str(ROOT / 'system/bin/bonsai-grow'))
                            self.assertEqual(tree['terminal_leaf_palette'](),
                                             [palette[key] for key in ('primary', 'secondary', 'tertiary')])
                            ink = tree['specimen_palette'](42)['leaf4']
                            self.assertIn(ink, tree['render'](30, 42, True))
                    for role, picked in (('primary', first), ('secondary', second)):
                        if not picked:
                            continue
                        distance = abs(hue(palette[role]) - hue(picked))
                        self.assertLess(min(distance, 1 - distance), .045)
                        container_distance = abs(hue(palette[role + 'Container']) - hue(picked))
                        self.assertLess(min(container_distance, 1 - container_distance), .08)
            command[4] = 'dark'
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual(output.read_bytes(), automatic)

    def test_invalid_and_failed_picks_leave_previous_palette_intact(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            output = folder / 'colors.json'
            output.write_text('previous palette')
            command = ['bash', str(GENERATOR), '/missing.png', 'scheme-content', 'dark', str(CONFIG), str(output)]
            for picks in (['#123;echo bad', ''], ['#12', ''], ['', '#abcd']):
                result = subprocess.run(command + picks, capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(output.read_text(), 'previous palette')
            fake = folder / 'matugen'
            fake.write_text('#!/bin/sh\nexit 1\n')
            fake.chmod(0o755)
            env = dict(os.environ, PATH=str(folder) + os.pathsep + os.environ['PATH'])
            result = subprocess.run(command + ['#123456', ''], env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), 'previous palette')


@unittest.skipUnless(Path('/usr/lib/qt6/bin/qmltestrunner').exists(), 'Qt Quick Test required')
class WallpaperSamplerTests(unittest.TestCase):
    def test_pixel_sampling_fit_margins_and_resize(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            image(folder / 'wall paper #1.png')
            shutil.copyfile(SHELL / 'modules/widgets/dashboard/controls/WallpaperSampler.qml', folder / 'WallpaperSampler.qml')
            (folder / 'tst_sampler.qml').write_text('''import QtQuick
import QtTest
Item {
    width: 300; height: 300
    WallpaperSampler { id: sampler; width: 200; height: 200; source: "wall%20paper%20%231.png" }
    SignalSpy { id: spy; target: sampler; signalName: "picked" }
    TestCase {
        name: "WallpaperSampler"
        when: windowShown
        function test_pixels() {
            tryVerify(() => sampler.ready);
            compare(sampler.sampleAt(25, 100), "#d21e28");
            compare(sampler.sampleAt(175, 100), "#1e3cd2");
            compare(sampler.sampleAt(25, 10), "");
            mouseClick(sampler, 25, 10);
            compare(spy.count, 0);
            mouseClick(sampler, 175, 100);
            compare(spy.count, 1);
            compare(spy.signalArguments[0][0], "#1e3cd2");
            sampler.forceActiveFocus();
            for (let i = 0; i < 5; i++) keyClick(Qt.Key_Left, Qt.ShiftModifier);
            keyClick(Qt.Key_Return);
            compare(spy.count, 2);
            compare(spy.signalArguments[1][0], "#d21e28");
            sampler.width = 100;
            wait(50);
            tryVerify(() => sampler.ready);
            compare(sampler.sampleAt(10, 100), "#d21e28");
            compare(sampler.sampleAt(90, 100), "#1e3cd2");
            compare(sampler.sampleAt(10, 60), "");
            sampler.width = 200;
            wait(50);
            tryVerify(() => sampler.ready);
            sampler.zoomAt(2, 50, 100);
            wait(50);
            tryVerify(() => sampler.ready);
            compare(sampler.zoom, 2);
            compare(sampler.sampleAt(50, 100), "#d21e28");
            compare(sampler.sampleAt(125, 100), "#d21e28");
            compare(sampler.sampleAt(175, 100), "#1e3cd2");
            const pickedBeforeDrag = spy.count;
            mousePress(sampler, 175, 100);
            mouseMove(sampler, 25, 100, 50);
            mouseRelease(sampler, 25, 100);
            wait(50);
            tryVerify(() => sampler.ready);
            compare(spy.count, pickedBeforeDrag);
            compare(sampler.panX, -100);
            compare(sampler.sampleAt(25, 100), "#1e3cd2");
            compare(sampler.sampleAt(-1, 100), "");
            sampler.resetView();
            wait(50);
            tryVerify(() => sampler.ready);
            compare(sampler.zoom, 1);
            compare(sampler.panX, 0);
            compare(sampler.sampleAt(25, 10), "");
            mouseWheel(sampler, 50, 100, 0, 120);
            wait(50);
            tryVerify(() => sampler.ready);
            compare(sampler.zoom, 1.25);
            compare(sampler.sampleAt(50, 100), "#d21e28");
            sampler.forceActiveFocus();
            keyClick(Qt.Key_0);
            wait(50);
            tryVerify(() => sampler.ready);
            compare(sampler.zoom, 1);
            sampler.zoomAt(100, 100, 100);
            compare(sampler.zoom, 8);
            sampler.source = "missing.png";
            compare(sampler.zoom, 1);
            tryVerify(() => !sampler.ready);
            compare(sampler.sampleAt(10, 100), "");
        }
    }
}''')
            runtime = folder / 'runtime'
            runtime.mkdir(mode=0o700)
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                       QT_QPA_PLATFORMTHEME='basic', XDG_RUNTIME_DIR=str(runtime))
            result = subprocess.run(['/usr/lib/qt6/bin/qmltestrunner', '-input', str(folder)],
                                    env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(shutil.which('node'), 'Node required')
class SavedWallpaperPicksTests(unittest.TestCase):
    def test_picks_are_isolated_per_wallpaper_and_reset_preserves_others(self):
        source = SHELL / 'modules/widgets/dashboard/wallpapers/Wallpaper.qml'
        code = r'''
const fs = require('fs'), assert = require('assert');
const source = fs.readFileSync(process.argv[1], 'utf8');
const start = source.indexOf('    function setPickedAccentColors(');
const end = source.indexOf('\n    // property string mpvSocket:', start);
const wallpaperAdapter = {wallpaperAccentColors: {}, activeColorPreset: 'preset'};
let currentWallpaper = '/pictures/first.png', generated = 0;
const Qt = {callLater: fn => fn()};
function runMatugenForCurrentWallpaper() { generated++; }
eval(source.slice(start, end));
setPickedAccentColors(['#102030', '#405060']);
assert.deepStrictEqual(wallpaperAdapter.wallpaperAccentColors[currentWallpaper], ['#102030', '#405060']);
assert.strictEqual(wallpaperAdapter.activeColorPreset, '');
currentWallpaper = '/pictures/second.png';
setPickedAccentColors(['#abcdef', '']);
currentWallpaper = '/pictures/first.png';
setPickedAccentColors(['', '']);
assert.strictEqual(wallpaperAdapter.wallpaperAccentColors[currentWallpaper], undefined);
assert.deepStrictEqual(wallpaperAdapter.wallpaperAccentColors['/pictures/second.png'], ['#abcdef', '']);
setPickedAccentColors(['not a color', '']);
currentWallpaper = '';
setPickedAccentColors(['#abcdef', '']);
assert.strictEqual(generated, 3);
console.log('Per-wallpaper choices and reset verified');
'''
        result = subprocess.run(['node', '-e', code, str(source)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
class PaletteSettingsCompileTests(unittest.TestCase):
    def test_settings_compile(self):
        with tempfile.TemporaryDirectory(prefix='palette-qml-') as tmp:
            folder = Path(tmp)
            for directory in ('modules', 'config', 'assets'):
                shutil.copytree(SHELL / directory, folder / directory)
            (folder / 'shell.qml').write_text('''import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.config
import qs.modules.globals
import qs.modules.theme
import qs.modules.services
import qs.modules.components
import qs.modules.widgets.dashboard.controls
import qs.modules.widgets.dashboard.wallpapers
ShellRoot {
    Timer {
        interval: 10; running: true
        onTriggered: {
            for (const path of ["modules/widgets/dashboard/controls/PaletteSettings.qml"]) {
                const component = Qt.createComponent(path);
                if (component.status !== Component.Ready) {
                    console.error(component.errorString());
                    Qt.exit(1);
                    return;
                }
            }
            const settings = Qt.createComponent("modules/widgets/dashboard/controls/PaletteSettings.qml").createObject(null, {width: 640});
            if (!settings) { Qt.exit(2); return; }
            console.log("PALETTE SETTINGS READY");
            Qt.quit();
        }
    }
}''')
            runtime = folder / 'runtime'
            runtime.mkdir(mode=0o700)
            env = dict(os.environ, HOME=str(folder), XDG_RUNTIME_DIR=str(runtime),
                       QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_QPA_PLATFORMTHEME='basic')
            for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                env.pop(key, None)
            for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
                env[key] = str(folder / key.lower())
            result = subprocess.run(['qs', '-p', str(folder), '--no-color'], env=env,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PALETTE SETTINGS READY', result.stdout)


if __name__ == '__main__':
    unittest.main()
