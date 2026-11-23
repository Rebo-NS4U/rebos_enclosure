"""Exercise the style picker and surface finishes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image

APP = Path(__file__).resolve().parents[2] / "system/apps/shell"

SCENE = """import QtQuick
import QtQuick.Window
import Quickshell
import qs.config
import qs.modules.components
import qs.modules.widgets.dashboard.controls

ShellRoot {
    Window {
        visible: true
        width: 640
        height: 640
        ShellStyleSettings { id: picker; width: 620 }
        Row {
            id: sample
            ThemeButton { id: sampleButton; width: 110; height: 50; text: "Apply" }
            StyledRect { width: 160; height: 50; variant: "bg" }
        }
        SearchInput { id: sampleField; y: 580; width: 230; height: 42 }
    }
    function findOption(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children) {
            const result = findOption(child, name);
            if (result) return result;
        }
        return null;
    }
    Timer {
        interval: 120
        running: true
        repeat: true
        property int step: 0
        property bool capturing: false
        readonly property var buttons: ["default", "inset", "underline"]
        readonly property var backgrounds: ["default", "wash", "two-tone"]
        onTriggered: {
            if (!Config.themeReady || capturing) return;
            if (step === 9) {
                stop();
                Qt.quit();
                return;
            }
            const button = findOption(picker, "buttonFinish-" + buttons[step % 3]);
            const background = findOption(picker, "backgroundFinish-" + backgrounds[Math.floor(step / 3)]);
            if (!button.checked || !background.checked) {
                button.clicked();
                background.clicked();
                return;
            }
            capturing = true;
            sample.grabToImage(result => {
                result.saveToFile(Quickshell.env("HOME") + "/" + step + ".png");
                capturing = false;
                ++step;
            });
        }
    }
}
"""


class ShellFinishTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("qs") and shutil.which("xvfb-run"), "Requires Quickshell and Xvfb")
    def test_picker_changes_button_and_panel_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("modules", "config", "assets", "scripts", "version"):
                (root / name).symlink_to(APP / name)
            (root / "runtime").mkdir(mode=0o700)
            (root / "shell.qml").write_text(SCENE)
            env = dict(os.environ, HOME=directory, XDG_CONFIG_HOME=str(root / ".config"),
                       XDG_RUNTIME_DIR=str(root / "runtime"), QT_QPA_PLATFORM="xcb",
                       QT_QPA_PLATFORMTHEME="basic", QSG_RHI_BACKEND="opengl")
            for key in ("WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "NIRI_SOCKET"):
                env.pop(key, None)
            with (root / "log").open("w+") as log:
                try:
                    result = subprocess.run(["xvfb-run", "-a", "qs", "-p", str(root)], env=env, stdout=log,
                                            stderr=subprocess.STDOUT, timeout=20)
                except subprocess.TimeoutExpired:
                    log.seek(0)
                    self.fail(log.read()[-6000:])
                log.seek(0)
                output = log.read()
                self.assertEqual(result.returncode, 0, output)
                for error in ("ReferenceError", "TypeError", "Unable to assign", "Cannot assign"):
                    self.assertNotIn(error, output)
            saved = json.loads((root / ".config/rebos_shell/config/theme.json").read_text())
            self.assertEqual(saved["buttonFinish"], "underline")
            self.assertEqual(saved["backgroundFinish"], "two-tone")
            buttons, panels = [], []
            for step in range(9):
                with Image.open(root / f"{step}.png") as image:
                    buttons.append(image.crop((0, 0, 110, 50)).tobytes())
                    panels.append(image.crop((110, 0, 270, 50)).tobytes())
            self.assertEqual(len(set(buttons)), 3)
            self.assertEqual(buttons, buttons[:3] * 3)
            self.assertEqual(len(set(panels)), 3)
            for index in (0, 3, 6):
                self.assertEqual(panels[index:index + 3], [panels[index]] * 3)
