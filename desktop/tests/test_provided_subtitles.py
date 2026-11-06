"""Provided dialogue captions must pass structural and episode coverage checks."""
import sys
from pathlib import Path
import unittest
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'system/apps/media'))
from vlc_session import provided_cues_usable, read_cues


class ProvidedSubtitleTests(unittest.TestCase):
    def test_dialogue_and_episode_coverage(self):
        cues = [(i * 5, i * 5 + 3, f'I think you should come here now. What do we do about this? Line {i}') for i in range(200)]
        self.assertTrue(provided_cues_usable(cues, 1100))
        self.assertFalse(provided_cues_usable(cues, 2400))
        self.assertFalse(provided_cues_usable(cues, 600))

    def test_sparse_repeated_and_invalid_captions(self):
        self.assertFalse(provided_cues_usable([]))
        self.assertFalse(provided_cues_usable([(i*60, i*60+2, 'Sign') for i in range(20)]))
        self.assertFalse(provided_cues_usable([(i*5, i*5-1, str(i)) for i in range(20)]))
        self.assertFalse(provided_cues_usable([(i*5, i*5+3, '\ufffd'+str(i)) for i in range(20)]))

    def test_wrong_language_and_uncertain_text_fall_back(self):
        for text in ('Это русский текст, а не английский.', 'Jeg ved ikke hvad du mener med det.', 'Dialogue line'):
            cues = [(i*5, i*5+3, f'{text} {i}') for i in range(200)]
            self.assertFalse(provided_cues_usable(cues, 1100))

    def test_legacy_and_utf16_subtitles_decode(self):
        text = '1\r\n00:00:01,000 --> 00:00:04,000\r\nI think you’re right. We should go now.\r\n'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'captions.srt'
            for encoding in ('utf-8-sig', 'utf-16', 'cp1252'):
                path.write_bytes(text.encode(encoding))
                cues = read_cues(path)
                self.assertEqual(len(cues), 1)
                self.assertEqual(cues[0][2], 'I think you’re right. We should go now.')
