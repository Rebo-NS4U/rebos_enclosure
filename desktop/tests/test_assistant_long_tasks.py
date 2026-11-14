"""Silence must not cancel ACP work or suppress its eventual updates."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
const source = require('node:fs').readFileSync(process.argv[1], 'utf8');
function extract(name) {
    const start = source.indexOf('    function ' + name + '(');
    const end = source.indexOf('\n    }', start) + 6;
    assert(start >= 0 && end > start);
    return source.slice(start, end);
}
const context = {
    agentTurnActive: true, turnFailureHandled: false, questionRequests: [],
    pendingPermissions: {}, statusText: 'Running', currentSessionId: 'session',
    suppressReplay: false, restarts: 0, received: [],
    failActiveTurn() { throw Error('inactivity cancelled live work'); },
    queueAssistantText(update) { context.received.push(update.content); },
    flushAssistantText() {},
};
context.turnWatchdog = {restart() { context.restarts++; }};
vm.createContext(context);
vm.runInContext(extract('checkTurnInactivity') + extract('handleSessionUpdate'), context);
// Repeated silent intervals, including a detached relay, preserve the live turn.
for (let i = 0; i < 10; i++) {
    context.bridgeAttached = i % 2 === 0;
    vm.runInContext('checkTurnInactivity()', context);
    assert.match(context.statusText, /Waiting for task progress/);
    assert.equal(context.agentTurnActive, true);
    assert.equal(context.turnFailureHandled, false);
}
vm.runInContext(`handleSessionUpdate({sessionId:'session', update: {
    sessionUpdate:'agent_message_chunk', content:'late result'
}})`, context);
assert.deepEqual(context.received, ['late result']);
assert.equal(context.restarts, 1);
assert.equal(context.statusText, 'Responding…');
for (const overrides of [
    {agentTurnActive:false}, {turnFailureHandled:true},
    {questionRequests:[{}]}, {pendingPermissions:{1:{}}}
]) {
    Object.assign(context, {agentTurnActive:true, turnFailureHandled:false,
        questionRequests:[], pendingPermissions:{}, statusText:'unchanged'}, overrides);
    vm.runInContext('checkTurnInactivity()', context);
    assert.equal(context.statusText, 'unchanged');
}
'''


@unittest.skipUnless(shutil.which('node'), 'Node.js required')
class AssistantLongTasksTest(unittest.TestCase):
    def test_silence_preserves_turn_and_late_updates(self):
        for app in ('assistant', 'shell'):
            with self.subTest(app=app):
                subprocess.run(['node', '-e', SCENARIO, str(
                    ROOT / 'system/apps' / app / 'modules/services/AiSession.qml'
                )], check=True, capture_output=True, text=True)
