"""Context lookup transport validation, timeout and request-scoped cleanup."""
import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('reader_meaning', ROOT / 'system/apps/shell/scripts/reader_meaning.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReaderMeaning(unittest.TestCase):
    def setUp(self):
        self.payload = {'token': 'test-1', 'term': 'bank', 'context': 'They stood on the bank of the river.'}
        self.calls = []
    def test_result_uses_dedicated_request_and_cancels_only_its_token(self):
        def call(action, value):
            self.calls.append((action, value))
            return {'busy': True} if action == 'readerMeaningStart' else {'text': 'The land beside the river.'}
        result = module.lookup(self.payload, runner=lambda *a, **k: None, call=call, sleep=lambda x: None)
        self.assertEqual(result['text'], 'The land beside the river.')
        self.assertEqual(self.calls[-1], ('readerMeaningCancel', 'test-1'))
    def test_oversized_context_is_rejected_before_starting_assistant(self):
        self.payload['context'] = 'x' * 1001
        with self.assertRaises(ValueError):
            module.lookup(self.payload, runner=lambda *a, **k: self.fail('Must not start assistant'))
    def test_start_error_is_shown_without_polling(self):
        def call(action, value):
            self.calls.append(action)
            return {'error': 'Enable the assistant first.'}
        result = module.lookup(self.payload, runner=lambda *a, **k: None, call=call)
        self.assertEqual(result['error'], 'Enable the assistant first.')
        self.assertNotIn('readerMeaningStatus', self.calls)
    def test_timeout_cleans_up_lookup(self):
        times = iter([0, 91])
        def call(action, value):
            self.calls.append((action, value)); return {'busy': True}
        result = module.lookup(self.payload, runner=lambda *a, **k: None, call=call, clock=lambda: next(times))
        self.assertIn('timed out', result['error'])
        self.assertEqual(self.calls[-1], ('readerMeaningCancel', 'test-1'))
    def test_poll_failure_still_cleans_up(self):
        def call(action, value):
            self.calls.append((action, value))
            if action == 'readerMeaningStatus': raise subprocess.TimeoutExpired('qs', 5)
            return {'busy': True}
        with self.assertRaises(subprocess.TimeoutExpired):
            module.lookup(self.payload, runner=lambda *a, **k: None, call=call, sleep=lambda x: None)
        self.assertEqual(self.calls[-1], ('readerMeaningCancel', 'test-1'))

if __name__ == '__main__': unittest.main()
