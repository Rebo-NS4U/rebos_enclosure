"""Compile and exercise the private assistant lookup with a fake ACP session."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

APP = Path(__file__).resolve().parents[2] / 'system/apps/assistant'
STUB_AI = '''pragma Singleton
import QtQuick
QtObject {
    property QtObject activeSession: QtObject {
        property var currentModel: ({name: "Configured backend"})
        property string currentAgentId: "configured-agent"
        property string currentSessionModelId: "selected-model"
        property string codexPreset: ""
    }
}
'''
HARNESS = '''import QtQuick
import Quickshell
import qs.modules.services
import qs.config
ShellRoot {
    id: test
    property string captured: ""
    property int created: 0
    property int cancelled: 0
    Component {
        id: fakeFactory
        QtObject {
            property bool sessionReady: true
            property bool switchingSessionModel: false
            property bool switchingDistillPreset: false
            property string currentSessionModelId: "default-model"
            property string modelSwitchError: ""
            property string lastError: ""
            property var questionRequests: []
            property var pendingPermissions: ({})
            property var currentChat: []
            property bool isBusy: false
            property bool sessionEnabled: true
            function setSessionModel(value) { currentSessionModelId = value; }
            function sendMessage(prompt, attachments) {
                if (currentSessionModelId !== "selected-model") throw Error("Configured model not selected");
                captured = prompt;
                currentChat = [{role: "assistant", content: "The land beside a river."}];
            }
            function flushAssistantText() {}
            function cancelGeneration(announce) { cancelled++; }
        }
    }
    Component.onCompleted: {
        ReaderMeaning.createSession = properties => {
            if (properties.preferredAgentId !== "configured-agent") throw Error("Wrong configured backend");
            created++; return fakeFactory.createObject(test);
        };
    }
    Timer {
        interval: 300; running: true; repeat: true
        property int phase: 0
        property int ticks: 0
        onTriggered: {
            try {
                if (++ticks > 30) throw Error("Lookup service timed out");
                if (!Config.aiReady) return;
                Config.ai.enabled = true;
                if (phase === 0) {
                    if (!JSON.parse(ReaderMeaning.start({token: "invalid"})).error || created) throw Error("Invalid request started backend");
                    ReaderMeaning.start({token: "test-one", term: "bank", context: "They stood beside the river bank."});
                    phase++; return;
                }
                if (ReaderMeaning.busy) return;
                const result = JSON.parse(ReaderMeaning.status("test-one"));
                if (result.text !== "The land beside a river." || result.provider !== "Configured backend") throw Error("Inline response missing");
                if (!captured.includes('"word":"bank"') || !captured.includes("Use ONLY this excerpt") || cancelled !== 1)
                    throw Error("Context prompt or private cleanup incorrect");
                ReaderMeaning.start({token: "test-two", term: "bank", context: "A river bank."});
                ReaderMeaning.cancel("test-one");
                if (!ReaderMeaning.busy) throw Error("Stale cancellation stopped new lookup");
                ReaderMeaning.cancel("test-two");
                if (ReaderMeaning.busy || ReaderMeaning.session || cancelled !== 2) throw Error("Owned request not cleaned up");
                console.log("PASS: configured backend/model, isolated prompt, response, validation and token-scoped cleanup");
                Qt.quit();
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
'''

@unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
class Service(unittest.TestCase):
    def test_private_context_lookup(self):
        with tempfile.TemporaryDirectory(prefix='reader-service-') as directory:
            root = Path(directory)
            for name in ('modules', 'config', 'assets'):
                shutil.copytree(APP / name, root / name)
            (root / 'modules/services/Ai.qml').write_text(STUB_AI)
            (root / 'shell.qml').write_text(HARNESS)
            (root / 'runtime').mkdir(mode=0o700)
            env = dict(os.environ, HOME=str(root), XDG_RUNTIME_DIR=str(root / 'runtime'),
                       QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_QPA_PLATFORMTHEME='basic')
            for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                env.pop(key, None)
            for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
                env[key] = str(root / key.lower())
            result = subprocess.run(['qs', '-p', str(root), '--no-color'], env=env,
                                    capture_output=True, text=True, timeout=20)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('PASS:', output)
            self.assertNotIn('ERROR', output)

if __name__ == '__main__': unittest.main()
