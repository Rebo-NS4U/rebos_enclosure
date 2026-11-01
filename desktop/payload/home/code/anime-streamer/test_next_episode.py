import unittest
from unittest.mock import Mock, patch
import menu_backend


class PlaybackHarness:
    publish_next_episode = menu_backend.Engine.publish_next_episode
    skip_to_next = menu_backend.Engine.skip_to_next


class NextEpisodeTests(unittest.TestCase):
    def setUp(self):
        self.engine = PlaybackHarness()
        self.engine.context = ({'id': 'show'}, ['1', '2', '3'], 0, 7)
        self.engine.session = Mock()
        self.engine.next_requested = False
        self.engine.next_episode_paused = False
        self.engine.episode_ended = False
        self.engine.file_loaded = True
        self.engine.duration = 1200
        self.engine.position = 100
        self.engine.last_next_offer = None
        self.engine.save_progress = Mock()
        self.engine.start_episode = Mock()
        self.sender = patch.object(menu_backend, 'send').start()
        self.addCleanup(patch.stopall)

    def offered(self):
        self.engine.publish_next_episode()
        return self.engine.last_next_offer['available']

    def test_only_final_ninety_seconds(self):
        self.assertFalse(self.offered())
        self.engine.position = 1110
        self.assertTrue(self.offered())
        self.engine.position = 800
        self.assertFalse(self.offered())

    def test_end_with_auto_next_disabled(self):
        self.engine.file_loaded = False
        self.engine.episode_ended = True
        self.assertTrue(self.offered())
        self.engine.skip_to_next()
        self.engine.start_episode.assert_called_once_with({'id': 'show'}, ['1', '2', '3'], 1, 7)
        self.engine.skip_to_next()
        self.assertEqual(self.engine.start_episode.call_count, 1)

    def test_preloaded_next_resumes_without_skipping(self):
        self.engine.context = ({'id': 'show'}, ['1', '2', '3'], 2, 7)
        self.engine.position = 0
        self.engine.next_episode_paused = True
        self.assertTrue(self.offered())
        self.engine.skip_to_next()
        self.engine.session.command.assert_called_once_with(['set_property', 'pause', False])
        self.engine.start_episode.assert_not_called()
        self.assertFalse(self.offered())

    def test_last_episode_and_closed_player_have_no_offer(self):
        self.engine.context = ({'id': 'show'}, ['1'], 0, 7)
        self.engine.episode_ended = True
        self.assertFalse(self.offered())
        self.engine.session = None
        self.engine.next_episode_paused = True
        self.assertFalse(self.offered())


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.engine = Mock()
        self.engine.play_token = 7
        self.engine.context = ({'id': 'show'}, ['1', '2'], 0, 7)
        self.engine.history = {}
        self.engine.settings = {'auto_next': True}
        self.engine.episode_ended = self.engine.next_requested = False
        self.sender = patch.object(menu_backend, 'send').start()
        self.addCleanup(patch.stopall)

    def event(self, reason):
        menu_backend.Engine.player_event(self.engine, {'event': 'end-file', 'reason': reason}, 7)

    def test_auto_next_once(self):
        self.event('eof')
        self.event('eof')
        self.engine.start_episode.assert_called_once_with({'id': 'show'}, ['1', '2'], 1, 7, automatic=True)

    def test_error_does_not_advance(self):
        self.event('error')
        self.engine.start_episode.assert_not_called()
        self.assertFalse(self.engine.episode_ended)

    def test_disabled_and_final_episode_do_not_advance(self):
        self.engine.settings['auto_next'] = False
        self.event('eof')
        self.engine.start_episode.assert_not_called()
        self.engine.episode_ended = False
        self.engine.settings['auto_next'] = True
        self.engine.context = ({'id': 'show'}, ['1', '2'], 1, 7)
        self.event('eof')
        self.engine.start_episode.assert_not_called()


if __name__ == '__main__':
    unittest.main()
