"""Exercise the real QML palette singleton without a desktop or theme exporters."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class WallpaperPaletteTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
    def test_wallpaper_colors_reload_and_missing_roles_keep_defaults(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / 'theme').mkdir()
            shutil.copyfile(root / 'system/apps/media/ui/modules/theme/Colors.qml', target / 'theme/Colors.qml')
            (target / 'theme/qmldir').write_text('singleton Colors 1.0 Colors.qml\n')
            cache = target / '.cache/rebos_shell'
            cache.mkdir(parents=True)
            palette = cache / 'colors.json'
            palette.write_text(json.dumps({'primary': '#123456', 'overSurface': '#abcdef'}))
            runtime = target / 'runtime'
            runtime.mkdir(mode=0o700)
            (target / 'shell.qml').write_text('''import QtQuick
import Quickshell
import Quickshell.Io
import "theme" as Theme
ShellRoot {
    Process {
        id: writer
        command: ["python3", "-c", "import pathlib,os; p=pathlib.Path(os.environ['HOME'])/'.cache/rebos_shell/colors.json'; p.write_text('{\\\"primary\\\":\\\"#654321\\\",\\\"overSurface\\\":\\\"#fedcba\\\"}')"]
    }
    Timer {
        interval: 250; running: true; repeat: true
        property int phase: 0
        property int polls: 0
        onTriggered: {
            if (++polls > 30) { console.error("Palette update timed out"); Qt.exit(1); }
            if (phase === 0) {
                if (Theme.Colors.primary.toString() !== "#123456") return;
                if (Theme.Colors.overSurface.toString() !== "#abcdef") { Qt.exit(1); return; }
                if (Theme.Colors.yellow.toString() !== "#dec56e") { Qt.exit(1); return; }
                phase++; writer.running = true; return;
            }
            if (Theme.Colors.primary.toString() !== "#654321") return;
            if (Theme.Colors.overSurface.toString() !== "#fedcba") { Qt.exit(1); return; }
            console.log("PASS: wallpaper palette initial load, live reload and fallback");
            Qt.quit();
        }
    }
}''')
            result = subprocess.run(['qs', '-p', str(target / 'shell.qml')],
                env=dict(os.environ, HOME=str(target), XDG_RUNTIME_DIR=str(runtime),
                         QT_QPA_PLATFORM='offscreen'), capture_output=True, text=True, timeout=15)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('PASS: wallpaper palette', output)
