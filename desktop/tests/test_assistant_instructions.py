"""Verify GitHub workflow delivery in real QML with isolated synthetic transport."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'payload/home/code/rebos-assistant'

SCENARIO = r'''
import QtQuick
import Quickshell
import qs.modules.services
ShellRoot {
    AiSession { id: session; sessionEnabled: false }
    function check(condition, message) {
        if (!condition) { console.error("FAIL", message); Qt.exit(1); throw new Error(message); }
    }
    function send(text) {
        session.queuedPrompt = {text: text, attachments: []};
        session.dispatchQueuedPrompt();
        return session.syntheticEnvelope.params.prompt;
    }
    function policy(prompt) { return prompt.find(item => item.text && item.text.startsWith("GitHub workflow:")); }
    Timer {
        interval: 100; running: true
        onTriggered: {
            session.sessionReady = true;
            session.currentAgentId = "codex";
            session.codexPreset = "";
            session.currentSessionId = "github-session";
            let initial = send("Edit a GitHub project");
            let github = policy(initial);
            check(github && github.text.includes("all GitHub-related project work") && github.text.includes("automatically committing and pushing tested task-scoped changes"), "policy covers all GitHub projects");
            check(github.text.includes("sandbox_permissions=require_escalated") && github.text.includes("Never log out, delete credentials"), "network approval and credential guidance reaches the agent");
            check(github.text.includes("preserve unrelated work") && github.text.includes("Never force-push"), "preserves work and approvals");
            check(send("Follow up").length === 1, "policy is sent only once per conversation");
            let chat = session.chatEnvelope();
            let state = session.bridgeState();
            check(chat.instructionGithubSessionId === "github-session:network-v2" && state.instructionGithubSessionId === "github-session:network-v2", "delivery persists in chat and bridge state");
            session.instructionGithubSessionId = "github-session"; // Previous policy version.
            session.syntheticTransportWorks = false;
            session.queuedPrompt = {text: "Offline", attachments: []};
            session.dispatchQueuedPrompt();
            check(session.instructionGithubSessionId === "github-session", "failed transport does not consume policy delivery");
            session.syntheticTransportWorks = true;
            let legacy = send("Continue an older chat");
            check(legacy.length === 2 && policy(legacy), "older chats receive only the new policy");
            check(send("Continue").length === 1, "older chat policy does not repeat");
            session.handleBridgeLine(JSON.stringify({bridge: "attached", seq: 1, state: state}));
            check(send("After bridge restoration").length === 1, "bridge restoration keeps policy delivery");
            session.currentSessionId = "fresh-github-session";
            check(policy(send("New chat")), "fresh conversations receive policy");
            session.currentAgentId = "distill";
            session.distillPresetReady = true;
            session.distillNeedsChatGPT = false;
            session.currentSessionId = "distill-github-session";
            check(policy(send("Other backend")), "policy reaches other assistant backends");
            check(send("Backend follow up").length === 1, "other backends do not repeat policy");
            console.log("PASS GitHub policy delivery, restoration, retries and multiple backends");
            Qt.quit();
        }
    }
}
'''

@unittest.skipUnless(shutil.which("qs"), "Quickshell required")
class AssistantGithubWorkflowTest(unittest.TestCase):
    def test_policy_delivery(self):
        with tempfile.TemporaryDirectory(prefix="ai-github-workflow-") as temporary:
            base = Path(temporary)
            package = base / "package"
            shutil.copytree(Path(__file__).parent / "fixtures/ai_sidebar", package)
            for relative in ("modules/services/AiSession.qml", "modules/services/AiQuestions.js"):
                target = package / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            service = package / "modules/services/AiSession.qml"
            source = service.read_text()
            start = source.index("    function restartAgentProcess() {")
            end = source.index("    function ensureConnection(", start)
            source = source[:start] + """    property int syntheticRestarts: 0
    function restartAgentProcess() { syntheticRestarts++; }

""" + source[end:]
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
            self.assertIn("PASS GitHub policy delivery, restoration, retries and multiple backends", output)

if __name__ == "__main__":
    unittest.main()
