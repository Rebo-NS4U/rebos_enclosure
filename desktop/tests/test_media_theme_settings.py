"""Exercise Streamer's real QML theme bindings and file watcher."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class ThemeSettingsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
    def test_oled_and_shell_preferences_reload_without_writing_settings(self):
        source = Path(__file__).resolve().parents[2] / 'system/apps/media/ui'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(source / 'config', root / 'config')
            shutil.copytree(source / 'modules/theme', root / 'modules/theme')
            settings = root / 'xdg/rebos_shell/config/theme.json'
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps(dict(oledMode=True, shellStyle='quiet', fontSize=18, controlBorderWidth=5)))
            palette = root / '.cache/rebos_shell/colors.json'
            palette.parent.mkdir(parents=True)
            palette.write_text(json.dumps(dict(background='#123456', surface='#234567',
                                              surfaceContainerLowest='#345678', surfaceDim='#456789')))
            runtime = root / 'runtime'
            runtime.mkdir(mode=0o700)
            (root / 'shell.qml').write_text(r'''import QtQuick
import Quickshell
import Quickshell.Io
import qs.config
import qs.modules.theme
ShellRoot {
    Process {
        id: writer
        command: ["python3", "-c", "import os,pathlib; (pathlib.Path(os.environ['XDG_CONFIG_HOME'])/'rebos_shell/config/theme.json').write_text('{\"oledMode\":true,\"lightMode\":true,\"shellStyle\":\"glyph\"}')"]
    }
    Timer {
        interval: 100; running: true; repeat: true
        property int phase: 0
        property int polls: 0
        onTriggered: {
            if (++polls > 60) { console.error("Theme update timed out"); Qt.exit(1); }
            if (phase === 0) {
                if (!Config.oledMode || Config.theme.fontSize !== 18) return;
                if (Config.controlBorderWidth !== 5 || Colors.background.toString() !== "#000000" || Colors.surface.toString() !== "#0f0f0f"
                    || Colors.surfaceContainerLowest.toString() !== "#000000"
                    || Colors.surfaceDim.toString() !== "#000000" || Styling.shellStyle !== "quiet") {
                    console.error("OLED roles or shell preferences mismatch"); Qt.exit(1); return;
                }
                phase++; writer.running = true; return;
            }
            if (!Config.lightMode || Config.oledMode || Styling.shellStyle !== "frosted") return;
            if (Config.controlBorderWidth !== 2 || Colors.background.toString() !== "#123456" || Colors.surface.toString() !== "#234567"
                || Colors.surfaceContainerLowest.toString() !== "#345678"
                || Colors.surfaceDim.toString() !== "#456789" || Config.theme.fontSize !== 14) {
                console.error("Light mode roles or fallback mismatch"); Qt.exit(1); return;
            }
            console.log("PASS: OLED, live settings, light mode and defaults"); Qt.quit();
        }
    }
}''')
            result = subprocess.run(['qs', '-p', str(root / 'shell.qml')],
                                    env=dict(os.environ, HOME=directory,
                                             XDG_CONFIG_HOME=str(root / 'xdg'),
                                             XDG_RUNTIME_DIR=str(runtime), QT_QPA_PLATFORM='offscreen'),
                                    capture_output=True, text=True, timeout=15)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('PASS: OLED', output)
            self.assertEqual(json.loads(settings.read_text()),
                             dict(oledMode=True, lightMode=True, shellStyle='glyph'))
