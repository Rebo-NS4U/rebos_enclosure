"""Opening VLC must not wait for remote catalogue or stream responses."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'system/apps/media'))
import app
import menu_backend
import menu_requests


class PlayerWindowLatencyTests(unittest.TestCase):
    def engine(self):
        engine = menu_backend.Engine.__new__(menu_backend.Engine)
        engine.play_token = 7
        engine.settings = app.DEFAULTS.copy()
        engine.session = engine.player = engine.context = None
        engine.stop_button = Mock()
        engine.play_status = Mock()
        engine.resolve = Mock()
        engine.launch_player = Mock()
        engine.save_progress = Mock()
        engine.close_captions = Mock()
        engine.publish_next_episode = Mock()
        return engine

    def test_window_opens_while_stream_resolution_is_pending(self):
        engine = self.engine()
        session = Mock(stop_count=0)
        order = []
        engine.resolve.side_effect = lambda *args: order.append('resolve')
        with patch.object(menu_backend, 'VlcSession', side_effect=lambda *args: order.append('window') or session) as factory:
            engine.start_episode({'id':'toradora-899','title':'Toradora!'}, ['1'], 0, 7)
            self.assertEqual(order, ['window', 'resolve'])
            session.load.assert_not_called()
            engine.ensure_player(7)
            factory.assert_called_once()
            ready = engine.resolve.call_args.args[1]
            ready(['https://example.com/video', '', '', ''])
            engine.launch_player.assert_called_once()

    def test_closing_window_cancels_pending_playback(self):
        engine = self.engine()
        session = Mock(stop_count=0)
        with patch.object(menu_backend, 'VlcSession', return_value=session) as factory, patch.object(menu_backend, 'send'):
            engine.start_episode({'id':'show','title':'Show'}, ['1'], 0, 7)
            ready = engine.resolve.call_args.args[1]
            callback = factory.call_args.args[1]
            callback({'event':'process-exited','code':0})
            self.assertEqual(engine.play_token, 8)
            ready(['https://example.com/video', '', '', ''])
            engine.launch_player.assert_not_called()

    def test_resolution_failure_closes_only_unused_preparation_window(self):
        engine = self.engine()
        session = Mock(stop_count=0)
        with patch.object(menu_backend, 'VlcSession', return_value=session) as factory:
            engine.start_episode({'id':'show','title':'Show'}, ['1'], 0, 7)
            engine.resolve.call_args.args[2]('Source unavailable')
            session.close.assert_called_once()
            self.assertIsNone(engine.session)
            self.assertFalse(factory.call_args.args[1]({'event':'process-exited','code':1}))
            engine.play_status.set_text.assert_called_with('Source unavailable')
        engine.session = session
        engine.context = ({'id':'existing'}, ['1'], 0, 7)
        session.close.reset_mock()
        engine.discard_preparing_player(7)
        session.close.assert_not_called()

    def test_quick_play_opens_window_before_episode_discovery(self):
        engine = Mock(play_token=7)
        order = []
        engine.ensure_player.side_effect = lambda token: order.append('window')
        engine.background.side_effect = lambda *args: order.append('discovery')
        menu_requests.dispatch({'action':'quick_play','show':{'id':'show','title':'Show'}}, engine, Mock())
        self.assertEqual(order, ['window', 'discovery'])
        engine.background.call_args.args[2]('Could not discover episodes')
        engine.discard_preparing_player.assert_called_once_with(7)

    def test_stale_request_does_not_open_a_window(self):
        engine = self.engine()
        with patch.object(menu_backend, 'VlcSession') as factory:
            engine.start_episode({'id':'show','title':'Show'}, ['1'], 0, 6)
            factory.assert_not_called()
            engine.resolve.assert_not_called()
