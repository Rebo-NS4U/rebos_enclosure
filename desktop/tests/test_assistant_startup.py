"""Compile the shipped assistant UI without opening a desktop or starting agents."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

APP = Path(__file__).resolve().parents[2] / 'system/apps/assistant'
HARNESS = '''import QtQuick
import Quickshell
import qs.modules.sidebar
import qs.modules.globals
import qs.modules.services
import qs.modules.components
import qs.modules.theme
import qs.config
ShellRoot {
    // Both older sidebars and the newer two-mode caller must remain loadable.
    Component { ModelSelectorPopup { agentSelection: true } }
    Component { ModelSelectorPopup { agentSelection: false } }
    Timer {
        interval: 10
        running: true
        onTriggered: {
            let sidebar = Qt.createComponent("modules/sidebar/AssistantSidebar.qml");
            if (sidebar.status !== Component.Ready) {
                console.error(sidebar.errorString());
                Qt.exit(1);
            } else {
                console.log("ASSISTANT COMPONENT READY");
                Qt.quit();
            }
        }
    }
}
'''


@unittest.skipUnless(shutil.which('qs'), 'Quickshell required for QML compilation')
class AssistantStartupTests(unittest.TestCase):
    def test_sidebar_and_model_picker_compile(self):
        app = Path(os.environ.get('REBOS_ASSISTANT_TEST_APP', str(APP)))
        with tempfile.TemporaryDirectory(prefix='rebos-qml-test-') as temporary:
            root = Path(temporary)
            for directory in ('modules', 'config', 'assets'):
                shutil.copytree(app / directory, root / directory)
            (root / 'shell.qml').write_text(HARNESS)
            (root / 'runtime').mkdir(mode=0o700)
            environment = dict(os.environ, HOME=str(root),
                               XDG_RUNTIME_DIR=str(root / 'runtime'),
                               QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                               QT_QPA_PLATFORMTHEME='basic')
            for key, directory in [('XDG_CONFIG_HOME', 'config-home'),
                                   ('XDG_CACHE_HOME', 'cache'),
                                   ('XDG_DATA_HOME', 'data'), ('XDG_STATE_HOME', 'state')]:
                environment[key] = str(root / directory)
            for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                environment.pop(key, None)
            result = subprocess.run(['qs', '-p', str(root), '--no-color'],
                                    env=environment, capture_output=True, text=True, timeout=20)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('ASSISTANT COMPONENT READY', output)


if __name__ == '__main__':
    unittest.main()
