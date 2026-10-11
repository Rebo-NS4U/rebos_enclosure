"""Exercise model switching and search in real QML with synthetic ACP replies."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

SCENARIO = r'''
import QtQuick
import Quickshell
import qs.modules.services
import qs.modules.sidebar
ShellRoot {
    id: test
    readonly property var sent: Ai.syntheticEnvelope
    function check(condition, message) {
        if (!condition) { console.error("FAIL", message); Qt.exit(1); }
    }
    function findNamed(item, name) {
        if (item.objectName === name) return item;
        for (let child of item.children || []) {
            let found = findNamed(child, name);
            if (found) return found;
        }
        return null;
    }
    Window {
        visible: true
        width: 340; height: 500
        AssistantModelPicker { id: picker; width: 320; expanded: true }
    }
    Timer {
        interval: 100; running: true
        onTriggered: {

            Ai.sessionReady = true;
            Ai.currentSessionId = "synthetic-session";
            Ai.updateSessionConfiguration({configOptions: [{id: "model", category: "model", currentValue: "first", options: [
                {value: "first", name: "First model", description: "Everyday tasks"},
                {value: "second", name: "Second model", description: "Complex tasks"}
            ]}]});
            check(Ai.sessionModelName === "First model", "friendly current name");
            Ai.agentTurnActive = true;
            Ai.setSessionModel("second");
            check(!Ai.switchingSessionModel && !sent.method, "busy turn must block model change");
            Ai.agentTurnActive = false;
            Ai.setSessionModel("second");
            check(sent.method === "session/set_config_option" && sent.params.value === "second", "config RPC selection");
            check(Ai.switchingSessionModel && Ai.currentSessionModelId === "first", "wait for acknowledgement");
            Ai.handleResponse({id: sent.id, error: {message: "Unavailable"}});
            check(!Ai.switchingSessionModel && Ai.currentSessionModelId === "first" && Ai.modelSwitchError.includes("Unavailable"), "failed switch retains current model");
            Ai.setSessionModel("second");
            Ai.handleResponse({id: sent.id, result: {}});
            check(!Ai.switchingSessionModel && Ai.currentSessionModelId === "second" && !Ai.modelSwitchError, "successful switch");
            Ai.sessionConfigOptions = [];
            Ai.setSessionModel("first");
            check(sent.method === "session/set_model", "legacy model RPC");
            Ai.handleResponse({id: sent.id, result: {}});
            check(Ai.currentSessionModelId === "first", "legacy acknowledgement");
            Ai.syntheticTransportWorks = false;
            Ai.setSessionModel("second");
            check(!Ai.switchingSessionModel && Ai.modelSwitchError.length > 0, "disconnected transport cleanup");
            picker.expanded = true;
            let search = findNamed(picker, "assistantModelSearch");
            check(search !== null, "search field exists");
            search.text = "complex";
            check(picker.filteredModels.length === 1 && picker.filteredModels[0].modelId === "second", "search matches descriptions");
            search.text = "missing";
            check(picker.filteredModels.length === 0, "empty search result");
            search.text = "";
            check(picker.filteredModels.length === 2, "clear search restores models");
            console.log("PASS model picker selection and search");
            Qt.quit();
        }
    }
}
'''

@unittest.skipUnless(shutil.which("qs"), "Quickshell required")
class AiModelPickerTest(unittest.TestCase):
    def test_selection_and_search(self):
        with tempfile.TemporaryDirectory(prefix="ai-model-picker-") as temporary:
            base = Path(temporary)
            package = base / "package"
            shutil.copytree(ROOT / "tests/fixtures/ai_sidebar", package)
            for relative in ("modules/services/Ai.qml", "modules/sidebar/AssistantModelPicker.qml",
                             "modules/components/StyledRect.qml"):
                target = package / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            service = package / "modules/services/Ai.qml"
            source = service.read_text()
            start = source.index("    function sendEnvelope(envelope) {")
            end = source.index("    function sendRequest(", start)
            # Substitute only process I/O; keep actual request/config/reply handling.
            source = source[:start] + """    property var syntheticEnvelope: ({})
    property bool syntheticTransportWorks: true
    function sendEnvelope(envelope) {
        syntheticEnvelope = envelope;
        return syntheticTransportWorks;
    }

""" + source[end:]
            service.write_text(source)
            (package / "shell.qml").write_text(SCENARIO)
            runtime = base / "runtime"
            runtime.mkdir(mode=0o700)
            environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="",
                               XDG_RUNTIME_DIR=str(runtime), XDG_CACHE_HOME=str(base / "cache"))
            result = subprocess.run(["qs", "-p", str(package), "--no-color"], env=environment,
                                    capture_output=True, text=True, timeout=8)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output[-4000:])
            self.assertNotIn("FAIL", output)
            self.assertNotIn("TypeError", output)
            self.assertIn("PASS model picker selection and search", output)

if __name__ == "__main__":
    unittest.main()
