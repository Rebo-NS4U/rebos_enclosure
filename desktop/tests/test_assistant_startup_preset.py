"""Exercise startup selection and deferred model confirmation in real QML."""
from unittest.mock import patch
import unittest

import test_assistant_instructions as harness


SCENARIO = r'''
import QtQuick
import Quickshell
import qs.modules.services
ShellRoot {
    AiSession {
        id: session
        sessionEnabled: false
        chatDir: Quickshell.env("DWEEBO_TEST_CHAT_DIR")
    }
    Connections {
        target: session
        function onCurrentChatIdChanged() {
            if (session.currentChatId !== "custom") return;
            Qt.callLater(() => {
                check(session.currentSessionId === "saved-custom" && session.codexPreset === "",
                    "saved custom chat reopens without picking Do");
                console.log("PASS compact context, profile switches, restoration and retries");
                Qt.quit();
            });
        }
    }
    function check(ok, message) {
        if (!ok) { console.error("FAIL", message); Qt.exit(1); throw new Error(message); }
    }
    Timer {
        interval: 100; running: true
        onTriggered: {
            check(session.codexPreset === "coding", "fresh startup selects Do");
            session.handleBridgeLine(JSON.stringify({bridge: "attached", state: {
                currentAgentId: "codex", sessionReady: true,
                currentSessionId: "startup-test", agentTurnActive: true,
                sessionConfigOptions: [
                    {id: "model", currentValue: "gpt-6.1-terra", options: [{value: "gpt-6.2-sol"}]},
                    {id: "reasoning_effort", currentValue: "low", options: [{value: "medium"}]}
                ]
            }}));
            check(session.codexPresetName === "dweebo-Do", "legacy checkpoint with no saved selection selects Do");
            check(session.agentTurnActive && session.currentSessionModelId !== "gpt-6.2-sol", "restored work is retained");
            check(!session.syntheticEnvelope.method && session.syntheticRestarts === 0, "startup sends no model RPC or restart");
            session.agentTurnActive = false;
            session.queuedPrompt = {text: "Next message", attachments: []};
            session.dispatchQueuedPrompt();
            check(session.syntheticEnvelope.method === "session/set_config_option", "model change precedes prompt");
            check(session.syntheticEnvelope.params.value === "gpt-6.2-sol" && session.queuedPrompt, "Do model requested and prompt waits");
            let options = JSON.parse(JSON.stringify(session.sessionConfigOptions));
            options[0].currentValue = "gpt-6.2-sol";
            session.handleResponse({id: session.syntheticEnvelope.id, result: {configOptions: options}});
            check(session.syntheticEnvelope.params.value === "medium" && session.queuedPrompt, "effort confirmation also precedes prompt");
            options[1].currentValue = "medium";
            session.handleResponse({id: session.syntheticEnvelope.id, result: {configOptions: options}});
            check(session.syntheticEnvelope.method === "session/prompt" && !session.queuedPrompt, "prompt follows both confirmations");
            session.handleBridgeLine(JSON.stringify({bridge: "attached", state: {
                currentAgentId: "codex", codexPreset: "light_coding", agentTurnActive: false
            }}));
            check(session.codexPreset === "light_coding", "explicit named choice is preserved");
            session.handleBridgeLine(JSON.stringify({bridge: "attached", state: {
                currentAgentId: "codex", codexPreset: "", agentTurnActive: false
            }}));
            check(session.codexPresetName === "Custom Codex", "explicit custom checkpoint stays custom");
            session.queuedPrompt = {text: "Continue with custom settings", attachments: []};
            session.dispatchQueuedPrompt();
            check(session.syntheticEnvelope.method === "session/prompt", "custom checkpoint sends prompt without overriding model or effort");
            session.handleBridgeLine(JSON.stringify({bridge: "attached", state: {
                currentAgentId: "distill", codexPreset: "", agentTurnActive: false
            }}));
            check(session.codexPreset === "", "other backends are preserved");
            session.currentAgentId = "codex";
            session.codexPreset = "coding";
            session.sessionReady = true;
            const targetModel = "gpt-6.1-terra";
            options[0].options.push({value: targetModel});
            session.updateSessionConfiguration({configOptions: options});
            session.syntheticTransportWorks = false;
            session.setSessionModel(targetModel);
            check(session.codexPreset === "coding" && !session.switchingSessionModel
                && session.currentSessionModelId === "gpt-6.2-sol",
                "transport failure preserves the confirmed model and profile");
            session.syntheticTransportWorks = true;
            session.setSessionModel(targetModel);
            check(session.codexPreset === "coding" && session.switchingSessionModel,
                "profile remains active while confirmation is pending");
            session.handleResponse({id: session.syntheticEnvelope.id, error: {message: "Rejected"}});
            check(session.codexPreset === "coding" && !session.switchingSessionModel && session.modelSwitchError,
                "backend rejection preserves the active profile");
            session.setSessionModel(targetModel);
            session.handleResponse({id: session.syntheticEnvelope.id, result: {configOptions: options}});
            check(session.codexPreset === "coding" && !session.switchingSessionModel && session.modelSwitchError,
                "a response returning the old model preserves the active profile");
            session.setSessionModel(targetModel);
            options[0].currentValue = targetModel;
            session.handleResponse({id: session.syntheticEnvelope.id, result: {configOptions: options}});
            check(session.codexPresetName === "Custom Codex" && !session.switchingSessionModel
                && session.currentSessionModelId === targetModel && !session.modelSwitchError,
                "confirmed manual model switch selects Custom Codex");
            const warning = 'Warning: This session was recorded with model `gpt-6.1-terra` but is resuming with `gpt-6.2-sol`. Consider switching back to `gpt-6.1-terra` as it may affect Codex performance.\n\n';
            function deliver(text, messageId) {
                session.handleSessionUpdate({sessionId: session.currentSessionId, update: {
                    sessionUpdate: "agent_message_chunk", messageId, content: {type: "text", text}
                }});
                session.flushAssistantText();
            }
            session.turnFailureHandled = false;
            session.codexPreset = "knowledge";
            options[0].currentValue = "gpt-6.2-sol";
            options[1].currentValue = "low";
            session.updateSessionConfiguration({configOptions: options});
            session.setCodexPreset("knowledge", true);
            deliver(warning);
            check(session.pendingCodexResumeWarning && !JSON.stringify(session.currentChat).includes(warning.trim()),
                "the resume warning waits for the selected model to be confirmed");
            options[0].currentValue = targetModel;
            session.handleResponse({id: session.syntheticEnvelope.id, result: {configOptions: options}});
            deliver(warning);
            check(!session.pendingCodexResumeWarning && !JSON.stringify(session.currentChat).includes(warning.trim()),
                "early and late warnings are dropped when the recorded model is restored");
            session.codexPreset = "knowledge";
            options[0].currentValue = "gpt-6.2-sol";
            session.updateSessionConfiguration({configOptions: options});
            session.setCodexPreset("knowledge", true);
            deliver(warning);
            session.handleResponse({id: session.syntheticEnvelope.id, error: {message: "Rejected"}});
            check(session.currentChat.some(item => item.role === "system" && item.content === warning.trim()),
                "the warning is visible when the recorded model could not be restored");
            deliver("Warning: A tool configuration changed.\n\n");
            check(JSON.stringify(session.currentChat).includes("A tool configuration changed"),
                "unrelated warnings remain visible");
            session.loadChat("custom");
        }
    }
}
'''


class AssistantStartupPresetTest(unittest.TestCase):
    def test_startup_and_confirmation(self):
        with patch.object(harness, "SCENARIO", SCENARIO):
            harness.AssistantInstructionsTest("test_prompt_delivery").test_prompt_delivery()


if __name__ == "__main__":
    unittest.main()
