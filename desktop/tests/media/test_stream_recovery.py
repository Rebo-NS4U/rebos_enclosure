import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request
import menu_backend
from stream_relay import StreamRelay


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.engine = menu_backend.Engine.__new__(menu_backend.Engine)
        self.engine.context = ({'id': 'anime', 'title': 'Show'}, ['1', '2'], 0, 7)
        self.engine.play_token = 7
        self.engine.session = Mock()
        self.engine.settings = {'mode': 'dub', 'quality': '1080p'}
        self.key = ('anime', '1', 'dub', '1080p')
        self.engine.resolved = {self.key: (0, 'stale URL')}
        self.engine.save_progress = Mock()
        self.engine.close_captions = Mock()
        self.engine.play_status = Mock()
        self.engine.start_episode = Mock()

    def test_refreshes_source_preserving_progress_and_same_player(self):
        with patch.object(menu_backend.GLib, 'timeout_add_seconds') as timer:
            self.assertTrue(self.engine.recover_stream(7))
            self.engine.save_progress.assert_called_once_with(force=True)
            self.assertNotIn(self.key, self.engine.resolved)
            self.engine.start_episode.assert_not_called()
            timer.call_args.args[1]()
        self.engine.start_episode.assert_called_once_with(*self.engine.context)
        self.engine.session.close.assert_not_called()

    def test_stop_or_episode_switch_cancels_delayed_recovery(self):
        for change in ('token', 'context', 'session'):
            with self.subTest(change=change), patch.object(menu_backend.GLib, 'timeout_add_seconds') as timer:
                self.setUp()
                self.engine.recover_stream(7)
                if change == 'token': self.engine.play_token += 1
                if change == 'context': self.engine.context = None
                if change == 'session': self.engine.session = Mock()
                timer.call_args.args[1]()
                self.engine.start_episode.assert_not_called()

    def test_recovery_is_bounded_and_recovers_budget_after_stable_playback(self):
        with patch.object(menu_backend.time, 'monotonic', return_value=100) as clock, \
             patch.object(menu_backend.GLib, 'timeout_add_seconds'):
            self.assertEqual([self.engine.recover_stream(7) for _ in range(4)], [True, True, True, False])
            clock.return_value = 221
            self.assertTrue(self.engine.recover_stream(7))


class UpstreamRetryTests(unittest.TestCase):
    def setUp(self):
        self.relay = StreamRelay.__new__(StreamRelay)
        self.relay.opener = Mock()
        self.request = Request('https://video.example/segment.ts?secret=private')

    def test_temporary_http_and_connection_errors_retry_same_segment(self):
        response = Mock()
        self.relay.opener.open.side_effect = [HTTPError(self.request.full_url, 503, 'busy', {}, None), TimeoutError(), response]
        with patch('stream_relay.time.sleep'), self.assertLogs(level='WARNING') as logs:
            self.assertIs(self.relay.open_upstream(self.request), response)
        self.assertEqual(self.relay.opener.open.call_count, 3)
        self.assertNotIn('secret', ''.join(logs.output))
        self.assertNotIn('private', ''.join(logs.output))

    def test_expired_signature_is_not_retried(self):
        self.relay.opener.open.side_effect = HTTPError(self.request.full_url, 403, 'expired', {}, None)
        with self.assertLogs(level='WARNING'), self.assertRaises(HTTPError):
            self.relay.open_upstream(self.request)
        self.assertEqual(self.relay.opener.open.call_count, 1)

    def test_persistent_outage_is_bounded(self):
        self.relay.opener.open.side_effect = TimeoutError()
        with patch('stream_relay.time.sleep'), self.assertLogs(level='WARNING'), self.assertRaises(TimeoutError):
            self.relay.open_upstream(self.request)
        self.assertEqual(self.relay.opener.open.call_count, 3)
