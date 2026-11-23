import json
import queue
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import menu_backend
from playback_context import PlaybackContext
from vlc_session import VlcSession


class CaptionPolicyTests(unittest.TestCase):
    def load(self, validate_provider=True, subtitle_choice=None, live_enabled=True):
        session = object.__new__(VlcSession)
        session.audio_normalization = True
        session.live_enabled = live_enabled
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
            session.load(('https://video', '', 'https://subtitle', ''), 'title', validate_provider=validate_provider,
                         subtitle_choice=subtitle_choice)
            session.apply(session.commands.get_nowait())
        session.loaded = True
        return session

    def test_whisper_defaults_even_when_english_tracks_are_available(self):
        session = self.load()
        data = json.loads(session.api.call_args.kwargs['data'])
        self.assertTrue(data['whisper_only'])
        session._poll_subtitles({})
        self.assertEqual(session.subtitle_source, 'whisper')
        session.apply(session.commands.get_nowait())
        session._poll_subtitles(dict(sid=3, subtitles=[dict(id=3, name='English')]))
        session.api.assert_called_with('subtitle', value=-1)
        self.assertEqual(session.subtitle_source, 'whisper')
        self.assertTrue(session.caption_requested)

    def test_embedded_track_is_used_when_whisper_is_disabled(self):
        session = self.load(live_enabled=False)
        session._poll_subtitles(dict(sid=-1, subtitles=[dict(id=3, name='English')]))
        session.api.assert_called_with('subtitle', value=3)
        self.assertEqual(session.subtitle_source, 'native:3')
        self.assertFalse(session.caption_requested)

    def test_youtube_retains_native_provider_captions(self):
        session = self.load(validate_provider=False, live_enabled=False)
        session.apply(session.commands.get_nowait())
        session.api.assert_called_with('addsubtitle', value='/provided.srt', select='true')
        session._poll_subtitles(dict(sid=2, subtitles=[dict(id=2, name='Provided English')]))
        self.assertEqual(session.subtitle_source, 'native:2')
        self.assertFalse(session.caption_requested)

    def test_remembered_off_overrides_embedded_english(self):
        session = self.load(subtitle_choice='off')
        session.last_state = dict(sid=3, subtitles=[dict(id=3, name='English')])
        session._poll_subtitles(session.last_state)
        session.api.assert_called_with('subtitle', value=-1)
        self.assertEqual(session.subtitle_source, 'off')

    def test_remembered_whisper_overrides_embedded_english(self):
        session = self.load(subtitle_choice='whisper')
        session._poll_subtitles(dict(sid=3, subtitles=[dict(id=3, name='English')]))
        self.assertEqual(session.subtitle_source, 'whisper')

    def test_remembered_embedded_track_matches_name_after_ids_change(self):
        session = self.load(subtitle_choice='Video English · English signs')
        session.last_state = dict(sid=3, subtitles=[dict(id=3, name='English'), dict(id=7, name='English signs')])
        session._poll_subtitles(session.last_state)
        session.api.assert_called_with('subtitle', value=7)
        self.assertEqual(session.subtitle_source, 'native:7')

    def test_remembered_provided_waits_and_overrides_embedded_english(self):
        session = self.load(subtitle_choice='provided')
        session.last_state = dict(sid=3, subtitles=[dict(id=3, name='English')])
        session._poll_subtitles(session.last_state)
        self.assertEqual(session.subtitle_source, 'off')
        session.provided_cues = [(index * 3, index * 3 + 2, f'I think we should go to the store with you ({index}).')
                                 for index in range(25)]
        session.subtitle_loading = False
        session._poll_subtitles(session.last_state)
        self.assertEqual(session.subtitle_source, 'provided')

    def test_choice_is_saved_per_series_and_loaded_for_another_episode(self):
        with TemporaryDirectory() as folder, patch.object(menu_backend, 'SUBTITLE_CHOICES', Path(folder) / 'choices.json'):
            show = dict(id='series-a', title='Series A')
            engine = menu_backend.Engine.__new__(menu_backend.Engine)
            engine.context = PlaybackContext(show, ['1', '2'], 0, 7)
            engine.session = Mock()
            engine.session.subtitle_tracks.return_value = {'options': [{'id': 'off', 'label': 'Off'}]}
            engine.subtitle_choices = {'series-b': 'whisper'}
            engine.file_loaded = True
            engine.select_subtitles('off')
            engine.session.command.assert_called_once_with(['subtitle-source', 'off'])

            reopened = menu_backend.Engine.__new__(menu_backend.Engine)
            reopened.subtitle_choices = menu_backend.app.read_json(menu_backend.SUBTITLE_CHOICES, {})
            self.assertEqual(reopened.subtitle_choices, {'series-a': 'off', 'series-b': 'whisper'})
            reopened.play_token = 7
            reopened.session = Mock()
            reopened.stop_button = Mock()
            reopened.close_captions = Mock()
            reopened.publish_next_episode = Mock()
            reopened.prefetch = SimpleNamespace()
            links = ('https://video', '', '', '')
            with patch.object(menu_backend, 'send'):
                reopened.launch_player(PlaybackContext(show, ['1', '2'], 1, 7), links, {})
            reopened.session.load.assert_called_once_with(links, 'Series A · Episode 2', paused=False,
                                                         validate_provider=True, subtitle_choice='off')


if __name__ == '__main__':
    unittest.main()
