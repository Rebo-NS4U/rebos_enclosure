import importlib.util
import hashlib
import json
import os
import tempfile
from unittest.mock import patch
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('timing', Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/reader_speech.py')
timing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timing)


class TimingTests(unittest.TestCase):
    def test_model_durations_control_onsets_not_word_length(self):
        # Both words have the same length, but the model speaks the second
        # after a long leading silence and a short first word.
        cues = timing.aligned_cues('cat dog', 'kat dog', [8, 1, 1, 1, 4, 9, 9, 9, 2], lambda w: {'cat': 'kat', 'dog': 'dog'}[w])
        spoken = [cue for cue in cues if cue[1] >= 0]
        self.assertEqual(spoken, [(8 / 40, 0, 3), (15 / 40, 4, 7)])
        self.assertEqual(cues[-1], (44 / 40, -1, -1))

    def test_context_pronunciation_and_utf16_offsets(self):
        cues = timing.aligned_cues('😀 read read', 'riːd rɛd', [1] * 10,
                                   lambda w: {'😀': '', 'read': 'riːd'}[w], offset=10)
        spoken = [cue for cue in cues if cue[1] >= 0]
        self.assertEqual([(a, b) for _, a, b in spoken], [(13, 17), (18, 22)])
        self.assertEqual(sorted(cues), cues)

    def test_previous_estimated_timing_cache_is_not_reused(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'XDG_RUNTIME_DIR': root}):
            path = timing.cached_page('some text', 'kokoro-heart', 1.05, [])
            old_key = json.dumps([2, 'some text', 'kokoro-heart', 1.05, []], ensure_ascii=True)
            old = path.parent / (hashlib.sha256(old_key.encode()).hexdigest() + '.json')
            old.write_text('[]')
            self.assertNotEqual(path, old)
            self.assertIsNone(timing.read_cached_page(path))

    def test_rejects_mismatched_model_tokens(self):
        with self.assertRaisesRegex(RuntimeError, 'timing shape'):
            timing.aligned_cues('hello', 'hello', [1], lambda w: w)


if __name__ == '__main__':
    unittest.main()
