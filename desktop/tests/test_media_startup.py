"""Playback must not wait for optional captions or repeat single-video metadata."""
from pathlib import Path
import queue
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'system/apps/media'))
import menu_requests
from vlc_session import VlcSession


class StartupTests(unittest.TestCase):
    def test_single_video_quick_play_skips_metadata_but_playlist_does_not(self):
        show = dict(id='youtube:abc', kind='youtube', title='Test', url='https://www.youtube.com/watch?v=abc')
        with patch.object(menu_requests.media_sources, 'details') as details:
            selected, episodes, index = menu_requests.card_selection(show, {})
            details.assert_not_called()
            self.assertEqual((episodes, index), ([show['url']], 0))
            details.return_value = dict(episodes=['one', 'two'])
            menu_requests.card_selection(dict(show, url=show['url']+'&list=PLabc'), {})
            details.assert_called_once()

    def session(self, folder):
        session = VlcSession.__new__(VlcSession)
        session.closed = threading.Event()
        session.commands = queue.Queue()
        session.generation = session.subtitle_revision = 0
        session.audio_normalization = False
        session.live_enabled = True
        session.logpath = Path(folder) / 'vlc.log'
        session.logpath.touch()
        session.api = Mock()
        session.public_stream = lambda url, referer: url
        return session

    def test_load_returns_while_subtitle_download_is_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            session = self.session(folder)
            entered, release, finished = threading.Event(), threading.Event(), threading.Event()
            def download(*args):
                entered.set()
                release.wait(3)
                finished.set()
                return '/tmp/subtitle.srt'
            session.subtitle_path = download
            try:
                session.apply(['load', ['https://example.com/video', '', 'https://example.com/sub', ''], 'Test', False, False])
                self.assertTrue(entered.wait(1))
                self.assertFalse(release.is_set())
                self.assertEqual(session.api.call_args.args[0], 'load')
                session.loaded = True
                release.set()
                command = session.commands.get(timeout=2)
                session.apply(command)
                session.api.assert_called_with('addsubtitle', value='/tmp/subtitle.srt', select='true')
            finally:
                release.set()
                finished.wait(2)

    def test_stale_captions_and_user_selection_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            session = self.session(folder)
            session.generation = 2
            session.loaded = session.requested = True
            session.finished = session.whisper_only = False
            session.apply(['subtitle-ready', 1, 0, '/tmp/old.srt', []])
            session.api.assert_not_called()
            session.subtitle_revision = 1
            session.apply(['subtitle-ready', 2, 0, '/tmp/current.srt', []])
            session.api.assert_called_with('addsubtitle', value='/tmp/current.srt', select='false')

    def test_provider_captions_arrive_without_overriding_user_choice(self):
        cues = [(i*5, i*5+3, f'I think you should come here now. What do we do? {i}') for i in range(30)]
        with tempfile.TemporaryDirectory() as folder:
            session = self.session(folder)
            session.loaded = session.requested = session.whisper_only = True
            session.finished = False
            session.last_state = {'duration': 150}
            session.subtitle_source = 'whisper'
            session.apply(['subtitle-ready', 0, 0, '/tmp/sub.srt', cues])
            self.assertEqual(session.subtitle_source, 'provided')
            self.assertEqual(session.cues, cues)
            session.subtitle_source = 'off'
            session.subtitle_revision = 1
            session.apply(['subtitle-ready', 0, 0, '/tmp/sub.srt', cues])
            self.assertEqual(session.subtitle_source, 'off')

    def test_captions_wait_for_input_before_attaching(self):
        with tempfile.TemporaryDirectory() as folder:
            session = self.session(folder)
            session.requested = True
            session.loaded = session.finished = session.whisper_only = False
            session.apply(['subtitle-ready', 0, 0, '/tmp/sub.srt', []])
            session.api.assert_not_called()
            session.loaded = True
            session.apply_pending_subtitle()
            session.api.assert_called_once_with('addsubtitle', value='/tmp/sub.srt', select='true')


if __name__ == '__main__':
    unittest.main()
