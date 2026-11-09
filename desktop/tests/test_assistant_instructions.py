"""Verify GitHub workflow delivery in real QML with isolated synthetic transport."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2] / 'system/apps/assistant'

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
    function policy(prompt) {
        let item = prompt.find(item => item.text && item.text.includes("GitHub workflow:"));
        return item ? {text: item.text.slice(item.text.indexOf("GitHub workflow:"))} : null;
    }
    Timer {
        interval: 100; running: true
        onTriggered: {
            check(JSON.stringify(session.builtInAgents.map(agent => agent.id).sort()) === JSON.stringify(["codex", "distill", "google"]), "only Codex, Distill and Gemini are offered");
            let stock = session.builtInAgents.find(item => item.id === "codex");
            let oldCommand = ["sh", "-lc", "CODEX_PATH=\"$(command -v codex)\" exec npx -y @agentclientprotocol/codex-acp"];
            check(JSON.stringify(session.normalizeAgent({command: oldCommand}, stock).command) === JSON.stringify(stock.command), "older stock launch commands adopt the current network settings");
            check(stock.command[2].includes("codex_workspace.py") && stock.command[2].includes('"network_access":true'), "launcher enables workspace networking through the compatibility helper");
            let custom = ["/custom/codex-acp", "--custom"];
            check(JSON.stringify(session.normalizeAgent({command: custom}, stock).command) === JSON.stringify(custom), "custom launch commands are preserved");
            session.sessionReady = true;
            session.currentAgentId = "codex";
            session.createNewChat();
            check(session.codexPreset === "coding", "new chats select dweebo-Do");
            let defaultMode = session.codexPresets.find(item => item.id === session.codexPreset);
            check(defaultMode.name === "dweebo-Do" && defaultMode.model === "gpt-6.1-sol" && defaultMode.effort === "medium", "default selects the Do model and effort");
            let deep = session.codexPresets.find(item => item.id === "deep");
            check(deep && deep.model === defaultMode.model && deep.effort === "high", "Deep offers Sol with high reasoning");
            session.sessionConfigOptions = [
                {id: "model", currentValue: deep.model},
                {id: "reasoning_effort", currentValue: "medium"}
            ];
            check(!session.codexPresetMatches(deep), "medium reasoning does not match Deep");
            session.sessionConfigOptions = [
                {id: "model", currentValue: deep.model},
                {id: "reasoning_effort", currentValue: "high"}
            ];
            check(session.codexPresetMatches(deep), "confirmed high reasoning matches Deep");
            let deepGuidance = session.standingInstructions(deep, false);
            check(deepGuidance.some(item => item.text.includes("primary sources") && item.text.includes("verify the requested behavior")), "Deep coding and research guidance reaches the prompt");
            let symphony = session.codexPresets.find(item => item.id === "symphony");
            check(symphony && symphony.model === defaultMode.model, "Symphony uses the existing Codex backend");
            session.currentSessionId = "symphony-test";
            session.codexPreset = "symphony";
            let guidance = session.standingInstructions(symphony, false);
            check(guidance[0].text.includes("WORKFLOW.md") && guidance[0].text.includes("Human review"), "Symphony workflow and handoff reach the prompt");
            session.instructionSessionId = session.currentSessionId;
            session.instructionModeGuidance = symphony.guidance;
            check(!session.standingInstructions(defaultMode, false).some(item => item.text.includes("Symphony coding profile")), "switching away does not resend Symphony guidance");
            session.sessionReady = true;
            session.codexPreset = "";
            session.currentSessionId = "github-session";
            let initial = send("Edit a GitHub project");
            check(initial[initial.length - 1].text === "Edit a GitHub project", "actual task follows standing context");
            let github = policy(initial);
            check(initial[0].text.startsWith("Standing preferences (context only"), "guidance is explicitly marked as context");
            check(initial[initial.length - 1].text === "Edit a GitHub project", "user task follows standing preferences");
            check(github && github.text.includes("all GitHub-related project work") && github.text.includes("automatically committing tested task-scoped changes locally"), "policy covers all GitHub projects");
            check(github.text.includes("Do not push automatically") && github.text.includes("Push button in GitHub Settings") && !github.text.includes("automatically committing and pushing"), "commits stay local until explicitly published");
            check(github.text.includes("sandbox_permissions=require_escalated") && github.text.includes("Never log out, delete credentials"), "network approval and credential guidance reaches the agent");
            check(github.text.includes("Dweebo enables network access") && github.text.includes("Host or administrator restrictions"), "guidance reflects configured access and managed limits");
            check(github.text.includes("preserve unrelated work") && github.text.includes("Never force-push"), "preserves work and approvals");
            check(github.text.includes("~/rebos_enclosure first") && github.text.includes("git rev-parse --show-toplevel") && github.text.includes("git remote -v"), "checkout discovery reaches the agent");
            check(github.text.includes("missing .git") && github.text.includes("recover any missed focused changes"), "copied installs require checkout discovery and source reconciliation");
            check(send("Follow up").length === 1, "policy is sent only once per conversation");
            let chat = session.chatEnvelope();
            let state = session.bridgeState();
            check(chat.instructionGithubSessionId === "github-session:checkout-discovery-v5" && state.instructionGithubSessionId === "github-session:checkout-discovery-v5", "delivery persists in chat and bridge state");
            session.instructionGithubSessionId = "github-session:commit-only-v4"; // Previous policy version.
            session.syntheticTransportWorks = false;
            session.queuedPrompt = {text: "Offline", attachments: []};
            session.dispatchQueuedPrompt();
            check(session.instructionGithubSessionId === "github-session:commit-only-v4", "failed transport does not consume policy delivery");
            session.syntheticTransportWorks = true;
            let legacy = send("Continue an older chat");
            check(legacy.length === 2 && policy(legacy), "older chats receive only the new policy");
            check(send("Continue").length === 1, "older chat policy does not repeat");
            session.handleBridgeLine(JSON.stringify({bridge: "attached", seq: 1, state: state}));
            check(session.codexPreset === "coding", "custom checkpoints adopt the startup default");
            session.codexPreset = ""; // Keep policy-only assertions independent of mode changes.
            check(send("After bridge restoration").length === 1, "bridge restoration keeps policy delivery");
            session.currentSessionId = "fresh-github-session";
            check(policy(send("New chat")), "fresh conversations receive policy");
            session.currentAgentId = "distill";
            session.distillPresetReady = true;
            session.distillNeedsChatGPT = false;
            session.currentSessionId = "distill-github-session";
            check(policy(send("Other backend")), "policy reaches other assistant backends");
            check(send("Backend follow up").length === 1, "other backends do not repeat policy");
            session.currentAgentId = "free-code";
            session.currentSessionId = "free-model-policy-test";
            let freePrompt = send("Say hello");
            check(freePrompt.length === 1 && freePrompt[0].text === "Say hello", "free backend answers the user rather than desktop policy");
            session.authenticated = true;
            session.pendingSessionAction = {kind: "new", cwd: "/tmp"};
            session.performSessionAction();
            let configuration = session.syntheticEnvelope.params;
            check(configuration.systemPrompt.mode === "append", "free backend receives standing instructions separately");
            check(policy(configuration.systemPrompt.content), "free system prompt retains GitHub policy");
            session.currentAgentId = "google";
            let google = session.findAgent("google");
            check(google && google.command[2].includes("google_agent.py"), "Google backend is registered");
            check(session.chooseAuthMethod({authMethods: [{id: "oauth-personal"}, {id: "gemini-api-key"}]}) === "gemini-api-key", "Google authenticates with its API key");
            check(session.chooseAuthMethod({authMethods: [{id: "oauth-personal"}]}) === "", "Google never falls back to personal OAuth");
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
