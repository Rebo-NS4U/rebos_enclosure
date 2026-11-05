"""Exercise startup selection and deferred model confirmation in real QML."""
from unittest.mock import patch
import unittest

import test_assistant_instructions as harness


SCENARIO = r'''
import QtQuick
import Quickshell
import qs.modules.services
ShellRoot {
    AiSession { id: session; sessionEnabled: false }
    function check(ok, message) {
        if (!ok) { console.error("FAIL", message); Qt.exit(1); throw new Error(message); }
    }
    Timer {
        interval: 100; running: true
        onTriggered: {
            check(session.codexPreset === "coding", "fresh startup selects Do");
            session.handleBridgeLine(JSON.stringify({bridge: "attached", state: {
                currentAgentId: "codex", codexPreset: "", sessionReady: true,
                currentSessionId: "startup-test", agentTurnActive: true,
                sessionConfigOptions: [
                    {id: "model", currentValue: "gpt-6-luna", options: [{value: "gpt-6.1-sol"}]},
                    {id: "reasoning_effort", currentValue: "low", options: [{value: "medium"}]}
                ]
            }}));
            check(session.codexPresetName === "dweebo-Do", "custom checkpoint selects Do");
            check(session.agentTurnActive && session.currentSessionModelId !== "gpt-6.1-sol", "restored work is retained");
            check(!session.syntheticEnvelope.method && session.syntheticRestarts === 0, "startup sends no model RPC or restart");
            session.agentTurnActive = false;
            session.queuedPrompt = {text: "Next message", attachments: []};
            session.dispatchQueuedPrompt();
            check(session.syntheticEnvelope.method === "session/set_config_option", "model change precedes prompt");
            check(session.syntheticEnvelope.params.value === "gpt-6.1-sol" && session.queuedPrompt, "Do model requested and prompt waits");
            let options = JSON.parse(JSON.stringify(session.sessionConfigOptions));
            options[0].currentValue = "gpt-6.1-sol";
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
                currentAgentId: "distill", codexPreset: "", agentTurnActive: false
            }}));
            check(session.codexPreset === "", "other backends are preserved");
            console.log("PASS GitHub policy delivery, restoration, retries and multiple backends");
            Qt.quit();
        }
    }
}
'''


class AssistantStartupPresetTest(unittest.TestCase):
    def test_startup_and_confirmation(self):
        with patch.object(harness, "SCENARIO", SCENARIO):
            harness.AssistantGithubWorkflowTest("test_policy_delivery").test_policy_delivery()


if __name__ == "__main__":
    unittest.main()
