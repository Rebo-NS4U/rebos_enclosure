"""Exercise actual QML permission handlers without a live backend."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const source = fs.readFileSync(process.argv[1], 'utf8');
const start = source.indexOf('    function handlePermissionRequest(');
const end = source.indexOf('    function handleSessionUpdate(', start);
const c = {autoApprove: false, currentChat: [{toolCallId: 'tool'}], pendingPermissions: {},
    agentTurnActive: true, questionRequests: [], turnWatchdog: {stop(){}, restart(){}},
    upsertToolCall(){}, findToolMessageIndex(){return 0}, saveCurrentChat(){}, responses: [],
    sendResponse(id, result){this.responses.push({id, result})}};
// QML methods resolve the session object as their scope.
c.sendResponse = (id, result) => c.responses.push({id, result});
vm.createContext(c);
vm.runInContext(source.slice(start, end), c);
const request = (id, options) => c.handlePermissionRequest(id, {toolCall:{toolCallId:'tool'}, options});
const options = [{kind:'reject_once',optionId:'no'}, {kind:'allow_always',optionId:'always'}, {kind:'allow_once',optionId:'once'}];
request(1, options);
assert.equal(c.responses.length, 0, 'off requires manual approval');
c.autoApprove = true;
const handlerStart = source.indexOf('    onAutoApproveChanged: {') + '    onAutoApproveChanged: {'.length;
const handlerEnd = source.indexOf('\n    property var pendingPermissions:', handlerStart);
vm.runInContext(source.slice(handlerStart, handlerEnd).replace(/}\s*$/, ''), c);
assert.equal(c.responses[0].result.outcome.optionId, 'once', 'enabling drains pending requests once');
request(2, options);
assert.equal(c.responses[1].result.outcome.optionId, 'once');
assert.equal(Object.keys(c.pendingPermissions).length, 0);
c.autoApprove = false;
request(3, options);
assert.equal(c.responses.length, 2, 'off stops future auto approvals');
c.rejectCommand(0);
assert.equal(c.responses[2].result.outcome.optionId, 'no');
c.autoApprove = true;
request(4, [{kind:'reject_once',optionId:'no'}]);
assert.equal(c.responses.length, 3, 'never auto select a rejection');
request(5, [{kind:'allow_always',optionId:'always'}]);
assert.equal(c.responses.length, 3, 'never create approval surviving the toggle');
assert(source.includes('onCurrentChatIdChanged: autoApprove = false'));
const other = vm.createContext({...c, autoApprove:false, pendingPermissions:{}, responses:[]});
assert.equal(other.autoApprove, false, 'independent sessions default off');
console.log('PASS auto approval lifecycle');
'''

class AutoApproveTest(unittest.TestCase):
    def test_permission_lifecycle(self):
        for package in ('assistant', 'shell'):
            with self.subTest(package=package):
                result = subprocess.run(['node', '-e', SCENARIO, str(ROOT / f'system/apps/{package}/modules/services/AiSession.qml')], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == '__main__':
    unittest.main()
