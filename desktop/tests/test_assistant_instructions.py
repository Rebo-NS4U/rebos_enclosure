"""Verify compact standing context and profile delivery in real QML with isolated synthetic transport."""
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
    function compact(prompt) {
        const text = prompt[0].text;
        return text.includes("/skills/desktop-work/SKILL.md")
            && text.includes("/skills/repository-work/SKILL.md")
            && text.includes("automatically make one local commit per independently verifiable change after checking it")
            && text.includes("Use a short, plain imperative subject")
            && text.includes("preserve unrelated staged and unstaged work")
            && text.includes("Push only when explicitly requested or initiated in GitHub Settings")
            && !text.includes("@HOME@") && !text.includes("WAYLAND_DISPLAY")
            && !text.includes("git rev-parse") && text.length < 2300;
    }
    Timer {
        interval: 100; running: true
        onTriggered: {
            check(JSON.stringify(session.builtInAgents.map(agent => agent.id).sort()) === JSON.stringify(["codex", "distill", "google"]), "registered backend list");
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
            check(defaultMode.name === "dweebo-Do" && defaultMode.model === "gpt-6.2-sol" && defaultMode.effort === "medium", "default selects the Do model and effort");
            // Exercise every role through the actual prompt builder and mode-change gate.
            const roleMarkers = {
                coding: "Coding mode:", deep: "root-cause debugging",
                symphony: "acceptance criterion", light_coding: "Linux configuration",
                quick: "command syntax", knowledge: "conceptual learning"
            };
            session.currentSessionId = "role-specialization-test";
            session.instructionSessionId = session.currentSessionId;
            session.deliveredSharedInstructionVersion = session.sharedInstructionVersion;
            for (const role of session.codexPresets) {
                session.instructionModeGuidance = "previous role";
                const changed = session.standingInstructions(role, false);
                check(changed.length === 1 && changed[0].text.includes(roleMarkers[role.id]) && changed[0].text.includes("governs subsequent turns"), role.id + " specialized guidance delivered after switching");
                session.instructionModeGuidance = role.guidance;
                check(session.standingInstructions(role, false).length === 0, role.id + " guidance does not repeat");
                check(session.standingInstructions(role, true)[0].text.includes(roleMarkers[role.id]), role.id + " guidance restored for forced delivery");
            }
            let deep = session.codexPresets.find(item => item.id === "deep");
            check(deep && deep.model === "gpt-6.2-astra" && deep.effort === "high", "Deep offers Astra 6.2 with high reasoning");
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
            let deepGuidance = session.standingInstructions(deep, false)[0].text;
            check(deepGuidance.includes("deep-investigation/SKILL.md") && deepGuidance.includes("two most plausible causes") && deepGuidance.includes("symptom, evidence and remaining uncertainty"), "Deep switch carries evidence into investigation");
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
            session.currentSessionId = "quick-session";
            let quick = session.codexPresets.find(item => item.id === "quick");
            session.codexPreset = quick.id;
            session.sessionConfigOptions = [
                {id: "model", currentValue: quick.model},
                {id: "reasoning_effort", currentValue: quick.effort}
            ];
            let initial = send("Hi");
            check(initial.length === 2 && initial[1].text === "Hi" && compact(initial), "fresh Quick chat receives compact context before the task");
            check(initial[0].text.startsWith("Standing preferences (context only"), "guidance is marked as context");
            check(send("Follow up").length === 1, "shared context is sent once");
            session.codexPreset = "";
            const customPrompt = send("Use custom settings");
            check(customPrompt.length === 2 && customPrompt[0].text.includes("No Dweebo profile is selected"), "custom settings retire earlier profile guidance");
            session.codexPreset = quick.id;
            const switched = send("Return to Quick");
            check(switched.length === 2 && switched[0].text.includes("Selected profile: dweebo-Quick")
                && !switched[0].text.includes("/skills/repository-work/"), "switch sends only new profile guidance");
            const state = session.bridgeState();
            check(session.chatEnvelope().instructionSessionId === "quick-session" && state.instructionSessionId === "quick-session", "delivery persists in chat and bridge state");
            session.handleBridgeLine(JSON.stringify({bridge: "attached", seq: 1, state: state}));
            check(send("After bridge restoration").length === 1, "bridge restoration keeps delivery");

            state.deliveredSharedInstructionVersion = 1;
            session.handleBridgeLine(JSON.stringify({bridge: "attached", seq: 2, state: state}));
            const upgraded = send("Resume pre-upgrade chat");
            check(upgraded.length === 2 && compact(upgraded)
                && !upgraded[0].text.includes("Selected profile:"), "previous-version chat receives updated commit instructions without repeating its profile");
            check(session.chatEnvelope().deliveredSharedInstructionVersion === session.sharedInstructionVersion,
                "shared instruction version is persisted");
            check(send("After upgrade").length === 1, "shared instructions are upgraded only once");

            session.currentSessionId = "fresh-session";
            session.syntheticTransportWorks = false;
            send("Offline");
            check(session.instructionSessionId === "quick-session", "failed transport does not consume delivery");
            session.syntheticTransportWorks = true;
            check(compact(send("Try again")), "retry receives compact context");
            session.currentAgentId = "distill";
            session.distillPresetReady = true;
            session.distillNeedsChatGPT = false;
            session.currentSessionId = "distill-session";
            check(compact(send("Other backend")), "Distill receives compact context");
            check(send("Backend follow up").length === 1, "Distill does not repeat shared context");
            session.currentAgentId = "free-code";
            session.currentSessionId = "free-model-policy-test";
            let freePrompt = send("Say hello");
            check(freePrompt.length === 1 && freePrompt[0].text === "Say hello", "free backend answers the user rather than desktop policy");
            session.authenticated = true;
            session.pendingSessionAction = {kind: "new", cwd: "/tmp"};
            session.performSessionAction();
            let configuration = session.syntheticEnvelope.params;
            check(configuration.systemPrompt.mode === "append", "free backend receives standing instructions separately");
            check(compact([{text: configuration.systemPrompt.content.map(item => item.text).join("\n")}]), "free system prompt routes task-specific procedures");
            session.currentAgentId = "google";
            let google = session.findAgent("google");
            check(google && google.command[2].includes("google_agent.py"), "Google backend is registered");
            check(session.chooseAuthMethod({authMethods: [{id: "oauth-personal"}, {id: "gemini-api-key"}]}) === "gemini-api-key", "Google authenticates with its API key");
            check(session.chooseAuthMethod({authMethods: [{id: "oauth-personal"}]}) === "", "Google never falls back to personal OAuth");
            console.log("PASS compact context, profile switches, restoration and retries");
            Qt.quit();
        }
    }
}
'''

@unittest.skipUnless(shutil.which("qs"), "Quickshell required")
class AssistantInstructionsTest(unittest.TestCase):
    def test_prompt_delivery(self):
        with tempfile.TemporaryDirectory(prefix="ai-instructions-") as temporary:
            base = Path(temporary)
            package = base / "package"
            shutil.copytree(Path(__file__).parent / "fixtures/ai_sidebar", package)
            for relative in ("modules/services/AiSession.qml", "modules/services/AiQuestions.js", "modules/services/DweeboDefaults.js"):
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
            chats = base / "chats"
            chats.mkdir()
            (chats / "custom.json").write_text(
                '{"version":2,"protocol":"acp","agentId":"codex","sessionId":"saved-custom","codexPreset":"","messages":[]}'
            )
            runtime = base / "runtime"
            runtime.mkdir(mode=0o700)
            environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="",
                               XDG_RUNTIME_DIR=str(runtime), XDG_CACHE_HOME=str(base / "cache"),
                               DWEEBO_TEST_CHAT_DIR=str(chats))
            result = subprocess.run(["qs", "-p", str(package), "--no-color"], env=environment,
                                    capture_output=True, text=True, timeout=8)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output[-4000:])
            self.assertNotIn("FAIL", output)
            self.assertNotIn("TypeError", output)
            self.assertIn("PASS compact context, profile switches, restoration and retries", output)

if __name__ == "__main__":
    unittest.main()
