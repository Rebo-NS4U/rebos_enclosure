import json
import unittest
from unittest.mock import Mock
from vlc_session import VlcSession


class CaptionPolicyTests(unittest.TestCase):
    def session(self):
        session = object.__new__(VlcSession)
        session.audio_normalization = True
        session.api = Mock()
        session.public_stream = lambda url, referer: url
        session.subtitle_path = Mock(return_value='/provided.srt')
        session.generation = 0
        session.logpath = Mock()
        session.logpath.stat.return_value.st_size = 0
        return session

    def load(self, whisper_only):
        session = self.session()
        session.apply(['load', ('https://video', '', 'https://subtitle', ''), 'title', False, whisper_only])
        return session, json.loads(session.api.call_args.kwargs['data'])

    def test_non_youtube_does_not_download_or_load_provided_subtitles(self):
        session, data = self.load(True)
        session.subtitle_path.assert_not_called()
        self.assertIn('sub-track=-1', data['options'])
        self.assertIn('no-sub-autodetect-file', data['options'])
        self.assertTrue(data['whisper_only'])
        session.apply(['set_property', 'sid', 2])
        self.assertEqual(session.api.call_count, 1)

    def test_youtube_retains_native_captions(self):
        session, data = self.load(False)
        session.subtitle_path.assert_called_once()
        self.assertIn('sub-file=/provided.srt', data['options'])
        self.assertNotIn('sub-track=-1', data['options'])
        session.apply(['captions-show'])
        self.assertFalse(session.caption_requested)

    def test_whisper_uses_one_osd_without_native_subtitle_track(self):
        session, data = self.load(True)
        session.apply(['captions-show'])
        self.assertTrue(session.caption_requested)
        self.assertEqual(session.api.call_count, 1)
        session.apply(['captions-clear'])
        self.assertFalse(session.caption_requested)
        session.api.assert_called_with('clear-caption')


if __name__ == '__main__':
    unittest.main()
