"""Exercise the shipped notification handler with two independent agent chats."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'payload/home'

SCENARIO = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
const source = require('node:fs').readFileSync(process.argv[1], 'utf8');
const start = source.indexOf('    function syncRequestNotifications() {');
const end = source.indexOf('\n    Timer {', start);
assert(start >= 0 && end > start);
assert(source.includes('session.pendingPermissionsChanged.connect(root.syncRequestNotifications)'));
const first = {channelId: 'first', questionRequests: [], pendingPermissions: {}};
const second = {channelId: 'second', questionRequests: [], pendingPermissions: {}};
const sent = [];
const selected = [];
const notices = {list: [], notifyInternal(n) {
    sent.push(n);
    this.list.push({...n, notificationId: sent.length, id: sent.length});
}, discardNotifications(ids) {
    this.list = this.list.filter(n => !ids.includes(n.notificationId));
}};
const globals = {assistantVisible: false, toggleAssistant() {this.assistantVisible = true;},
    assistantFocusRequested(value) {this.focused = value;}};
const context = {sessions: [first, second], notifiedRequestKeys: [], Notifications: notices,
    GlobalStates: globals};
context.root = {sessions: context.sessions, selectSession(s) {selected.push(s.channelId);}};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
const sync = () => vm.runInContext('syncRequestNotifications()', context);
first.questionRequests = [{requestId: 1, message: 'A question'}];
second.pendingPermissions = {'1': {toolCallId: 'git-push'}};
sync();
assert.equal(sent.length, 2);
assert.equal(sent[1].summary, 'Assistant needs permission');
assert.equal(sent[1].replaceKey, 'assistant-permission:second:1');
sync();
assert.equal(sent.length, 2, 'unchanged pending requests must not notify twice');
sent[1].actionHandlers.review();
assert.deepEqual(selected, ['second']);
assert.equal(globals.assistantVisible, true);
sent[1].actionHandlers.review();
assert.equal(globals.focused, true);
assert.equal(Object.keys(second.pendingPermissions).length, 1, 'review must not approve');
first.pendingPermissions = {'1': {toolCallId: 'git-fetch'}};
sync();
assert.equal(sent.length, 3, 'request IDs are scoped to a chat');
second.pendingPermissions = {};
sync();
assert(!notices.list.some(n => n.replaceKey === 'assistant-permission:second:1'));
const count = selected.length;
sent[1].actionHandlers.review();
assert.equal(selected.length, count, 'resolved approval action is inert');
context.sessions = [second];
context.root.sessions = context.sessions;
sync();
assert.equal(notices.list.length, 0, 'closed chats discard their notifications');
sent[2].actionHandlers.review();
assert.equal(selected.length, count, 'closed chat action is inert');
console.log('PASS question and permission notification lifecycle');
'''


@unittest.skipUnless(shutil.which('node'), 'Node.js required')
class AssistantPermissionNotificationsTest(unittest.TestCase):
    def test_notifications(self):
        for relative in ('code/rebos-assistant', '.config/quickshell'):
            with self.subTest(package=relative):
                result = subprocess.run(
                    ['node', '-e', SCENARIO, str(ROOT / relative / 'modules/services/Ai.qml')],
                    text=True, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
