import json
import queue
import threading
import unittest
from unittest.mock import Mock, patch
from vlc_session import VlcSession


class CaptionPolicyTests(unittest.TestCase):
    def session(self):
        session = object.__new__(VlcSession)
        session.audio_normalization = True
        session.api = Mock()
        session.public_stream = lambda url, referer: url
        session.subtitle_path = Mock(return_value='/provided.srt')
        session.generation = 0
        session.subtitle_revision = 0
        session.closed = threading.Event()
        session.commands = queue.Queue()
        session.logpath = Mock()
        session.logpath.stat.return_value.st_size = 0
        return session

    def load(self, whisper_only):
        session = self.session()
        with patch('vlc_session.threading.Thread') as worker:
            worker.return_value.start.side_effect = lambda: worker.call_args.kwargs['target']()
            session.apply(['load', ('https://video', '', 'https://subtitle', ''), 'title', False, whisper_only])
        return session, json.loads(session.api.call_args.kwargs['data'])

    def test_invalid_provider_captions_fall_back_without_native_track(self):
        session, data = self.load(True)
        session.subtitle_path.assert_called_once()
        self.assertIn('sub-track=-1', data['options'])
        self.assertIn('no-sub-autodetect-file', data['options'])
        self.assertTrue(data['whisper_only'])
        session.apply(['set_property', 'sid', 2])
        self.assertEqual(session.api.call_count, 1)

    def test_youtube_retains_native_captions(self):
        session, data = self.load(False)
        session.subtitle_path.assert_called_once()
        self.assertNotIn('sub-file=/provided.srt', data['options'])
        session.loaded = True
        session.apply(session.commands.get_nowait())
        session.api.assert_called_with('addsubtitle', value='/provided.srt', select='true')
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
