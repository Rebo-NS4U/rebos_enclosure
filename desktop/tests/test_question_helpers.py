"""Both application entry points share one question protocol implementation."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class QuestionHelperTests(unittest.TestCase):
    def exchange(self, messages):
        outputs = []
        for app in ('assistant', 'shell'):
            script = ROOT / 'system/apps' / app / 'scripts/ai_questions.py'
            response = subprocess.run(['python', str(script)],
                                      input='\n'.join(json.dumps(m) for m in messages)+'\n',
                                      capture_output=True, text=True, timeout=5)
            self.assertEqual(response.returncode, 0, response.stderr)
            outputs.append([json.loads(line) for line in response.stdout.splitlines()])
        self.assertEqual(outputs[0], outputs[1])
        return outputs[0]

    def initialize(self, forms=True):
        return {'id': 1, 'method': 'initialize', 'params': {
            'capabilities': {'elicitation': {'form': {}}} if forms else {}}}

    def call(self, identifier=2):
        return {'id': identifier, 'method': 'tools/call', 'params': {
            'name': 'ask_user_question', 'arguments': {'question': 'Choose', 'options': ['A', 'B']}}}

    def test_accept_preserves_original_request_id_and_answer(self):
        out = self.exchange([self.initialize(), self.call(), {'id': 'question-1',
                            'result': {'action': 'accept', 'content': {'answer': 'B'}}}])
        self.assertEqual(out[1]['method'], 'elicitation/create')
        self.assertEqual(out[1]['params']['requestedSchema']['properties']['answer']['enum'],
                         ['A', 'B', 'Something else'])
        self.assertEqual(out[2]['id'], 2)
        answer = json.loads(out[2]['result']['content'][0]['text'])
        self.assertEqual(answer, {'action': 'accept', 'content': {'answer': 'B'}})

    def test_cancel_drops_late_response_but_keeps_other_question(self):
        out = self.exchange([self.initialize(), self.call(), self.call(3),
            {'method': 'notifications/cancelled', 'params': {'requestId': 2}},
            {'id': 'question-1', 'result': {'action': 'accept'}},
            {'id': 'question-2', 'result': {'action': 'decline'}}])
        self.assertEqual(out[3]['method'], 'notifications/cancelled')
        self.assertEqual(out[3]['params']['requestId'], 'question-1')
        self.assertEqual(out[4]['id'], 3)
        self.assertEqual(len(out), 5)

    def test_missing_form_support_returns_tool_error(self):
        out = self.exchange([self.initialize(False), self.call()])
        self.assertTrue(out[1]['result']['isError'])
        self.assertNotIn('method', out[1])

    def test_invalid_message_then_ping_recovers(self):
        out = self.exchange([[], {'id': 4, 'method': 'ping'}])
        self.assertEqual(out[0]['error']['code'], -32700)
        self.assertEqual(out[1], {'jsonrpc': '2.0', 'id': 4, 'result': {}})
