"""Provided dialogue captions must pass structural and episode coverage checks."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'system/apps/media'))
from vlc_session import provided_cues_usable


class ProvidedSubtitleTests(unittest.TestCase):
    def test_dialogue_and_episode_coverage(self):
        cues = [(i * 5, i * 5 + 3, f'Dialogue line {i}') for i in range(200)]
        self.assertTrue(provided_cues_usable(cues, 1100))
        self.assertFalse(provided_cues_usable(cues, 2400))
        self.assertFalse(provided_cues_usable(cues, 600))

    def test_sparse_repeated_and_invalid_captions(self):
        self.assertFalse(provided_cues_usable([]))
        self.assertFalse(provided_cues_usable([(i*60, i*60+2, 'Sign') for i in range(20)]))
        self.assertFalse(provided_cues_usable([(i*5, i*5-1, str(i)) for i in range(20)]))
        self.assertFalse(provided_cues_usable([(i*5, i*5+3, '\ufffd'+str(i)) for i in range(20)]))
