"""Check Whisper cue boundaries through the subtitle file read by the player."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'system/apps/media'))
from live_subtitles import cues_from_whisper, write_srt
from vlc_session import read_cues


def segment(text, start=0, step=300):
    return {'tokens': [{'text': ' ' + word, 'offsets': {'from': start + i * step,
                                                        'to': start + i * step + 200}}
                       for i, word in enumerate(text.split())]}


def captions(*segments):
    return cues_from_whisper({'transcription': segments}, 0)


class SentenceCueTests(unittest.TestCase):
    def test_short_replies_and_quoted_endings(self):
        cues = captions(segment('Wait! Are you ready? “Yes.” Go.'))
        self.assertEqual([cue[2] for cue in cues], ['Wait!', 'Are you ready?', '“Yes.”', 'Go.'])
        self.assertEqual(cues[0][:2], (0, .3))
        self.assertEqual(cues[2][:2], (1.2, 1.5))

    def test_commas_titles_and_initials_inside_a_sentence(self):
        cues = captions(segment('Wait, Dr. J. Smith is here.'))
        self.assertEqual([cue[2] for cue in cues], ['Wait, Dr. J. Smith is here.'])

    def test_wrap_sentence_at_clause_in_player(self):
        text = 'When the train arrives, we can go back to the hotel.'
        cues = captions(segment(text))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'captions.srt'
            write_srt(path, cues)
            self.assertEqual(read_cues(path), [(0, 3.32, 'When the train arrives,\nwe can go back to the hotel.')])

    def test_long_sentence_changes_cue_at_a_clause(self):
        text = ('We waited on the platform, then we caught the last train '
                'all the way back to our little house near the sea.')
        cues = captions(segment(text))
        self.assertEqual(cues[0][2], 'We waited on the platform,')
        self.assertEqual(' '.join(c[2].replace('\n', ' ') for c in cues), text)
        for start, end, lines in cues:
            self.assertLessEqual(end - start, 6.12)
            self.assertLessEqual(len(lines.splitlines()), 2)
            self.assertLessEqual(max(map(len, lines.splitlines())), 42)

    def test_pause_breaks_unpunctuated_speech(self):
        cues = captions(segment('Stay here'), segment('keep watch', start=2200))
        self.assertEqual([c[2] for c in cues], ['Stay here', 'keep watch'])
        self.assertLess(cues[0][1], cues[1][0])

    def test_sentence_across_segments_in_mixed_audio(self):
        second = segment('the station.', start=800)
        second['tokens'][0]['text'] = 'the'
        translated = {'text': 'All aboard!', 'offsets': {'from': 1800, 'to': 2500}}
        cues = captions(segment('Welcome to'), second, translated)
        self.assertEqual([c[2] for c in cues], ['Welcome to the station.', 'All aboard!'])

    def test_translated_sentences_share_original_speech_timing(self):
        cues = captions({'text': 'Wait! Is Dr. Bell here?', 'offsets': {'from': 320, 'to': 2110}})
        self.assertEqual(cues, [(.32, 2.11, 'Wait!\nIs Dr. Bell here?')])
