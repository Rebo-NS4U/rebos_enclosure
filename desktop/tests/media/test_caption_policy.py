import json
import queue
import threading
import unittest
from unittest.mock import Mock, patch
from vlc_session import VlcSession


class CaptionPolicyTests(unittest.TestCase):
    def load(self, validate_provider=True):
        session = object.__new__(VlcSession)
        session.audio_normalization = True
        session.live_enabled = True
        session.api = Mock()
        session.public_stream = lambda url, referer: url
        session.subtitle_path = Mock(return_value='/provided.srt')
        session.generation = 0
        session.subtitle_revision = 0
        session.closed = threading.Event()
        session.commands = queue.Queue()
        session.logpath = Mock()
        session.logpath.stat.return_value.st_size = 0
        with patch('vlc_session.threading.Thread') as worker:
            worker.return_value.start.side_effect = lambda: worker.call_args.kwargs['target']()
            session.apply(['load', ('https://video', '', 'https://subtitle', ''), 'title', False, validate_provider])
        session.loaded = True
        return session

    def test_embedded_english_is_preferred_and_disables_generated_overlay(self):
        session = self.load()
        data = json.loads(session.api.call_args.kwargs['data'])
        self.assertNotIn('sub-track=-1', data['options'])
        self.assertFalse(data['whisper_only'])
        session.apply(session.commands.get_nowait())
        session._poll_subtitles({})
        self.assertEqual(session.subtitle_source, 'whisper')
        session._poll_subtitles(dict(sid=-1, subtitles=[dict(id=3, name='English')]))
        session.api.assert_called_with('subtitle', value=3)
        self.assertEqual(session.subtitle_source, 'native:3')
        self.assertFalse(session.caption_requested)

    def test_waits_for_provider_then_uses_ai_when_provider_is_unavailable(self):
        session = self.load()
        session._poll_subtitles({})
        self.assertEqual(session.subtitle_source, 'off')
        session.apply(session.commands.get_nowait())
        session._poll_subtitles({})
        self.assertEqual(session.subtitle_source, 'whisper')
        self.assertTrue(session.caption_requested)
        session.live_enabled = False
        session._poll_subtitles({})
        self.assertEqual(session.subtitle_source, 'off')

    def test_youtube_retains_native_provider_captions(self):
        session = self.load(validate_provider=False)
        session.apply(session.commands.get_nowait())
        session.api.assert_called_with('addsubtitle', value='/provided.srt', select='true')
        session._poll_subtitles(dict(sid=2, subtitles=[dict(id=2, name='Provided English')]))
        self.assertEqual(session.subtitle_source, 'native:2')
        self.assertFalse(session.caption_requested)


if __name__ == '__main__':
    unittest.main()
