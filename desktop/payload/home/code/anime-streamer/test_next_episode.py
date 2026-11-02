import unittest
from unittest.mock import Mock, patch
import menu_backend


class PlaybackHarness:
    publish_next_episode = menu_backend.Engine.publish_next_episode
    skip_to_next = menu_backend.Engine.skip_to_next
    media_title = staticmethod(menu_backend.Engine.media_title)


class NextEpisodeTests(unittest.TestCase):
    def setUp(self):
        self.engine = PlaybackHarness()
        self.show = {'id': 'show', 'title': 'Show'}
        self.engine.context = (self.show, ['1', '2', '3'], 0, 7)
        self.engine.session = Mock()
        self.engine.next_requested = False
        self.engine.next_episode_paused = False
        self.engine.episode_ended = False
        self.engine.file_loaded = True
        self.engine.chapter = -1
        self.engine.chapter_count = 0
        self.engine.chapter_name = ''
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

    def test_generic_chapters_never_replace_time_fallback(self):
        self.engine.chapter_count = 6
        self.engine.chapter = 3
        self.engine.position = 1190
        self.assertTrue(self.offered())
        self.engine.chapter = 4
        self.engine.position = 800
        self.assertFalse(self.offered())
        self.engine.chapter = 5
        self.assertFalse(self.offered())
        self.engine.chapter = 2
        self.assertFalse(self.offered())

    def test_named_credits_match_episode_length_and_never_intro(self):
        self.engine.chapter_count = 6
        self.engine.chapter = 5
        self.engine.chapter_name = 'End Credits'
        self.engine.position = 1000
        self.assertTrue(self.offered())
        self.engine.position = 200
        self.assertFalse(self.offered())
        self.engine.chapter_name = 'Opening Credits'
        self.assertFalse(self.offered())

    def test_short_video_does_not_offer_next_at_the_start(self):
        self.engine.context = (dict(self.show, kind='youtube'), ['one', 'two'], 0, 7)
        self.engine.duration = 30
        self.engine.position = 0
        self.assertFalse(self.offered())
        self.engine.position = 28
        self.assertTrue(self.offered())
        self.assertEqual(self.engine.last_next_offer['label'], 'Next video')

    def test_movie_never_offers_episode_navigation(self):
        self.engine.context = (dict(self.show, kind='movies'), ['movie', 'other'], 0, 7)
        self.engine.position = 1199
        self.assertFalse(self.offered())

    def test_preloaded_episode_is_not_offered_until_loaded(self):
        self.engine.next_episode_paused = True
        self.engine.file_loaded = False
        self.assertFalse(self.offered())

    def test_invalid_chapters_fall_back_to_time(self):
        self.engine.chapter_count = 6
        self.engine.chapter = -1
        self.assertFalse(self.offered())
        self.engine.position = 1110
        self.assertTrue(self.offered())

    def test_end_with_auto_next_disabled(self):
        self.engine.file_loaded = False
        self.engine.episode_ended = True
        self.assertTrue(self.offered())
        self.engine.skip_to_next()
        self.engine.start_episode.assert_called_once_with(self.show, ['1', '2', '3'], 1, 7)
        self.engine.skip_to_next()
        self.assertEqual(self.engine.start_episode.call_count, 1)

    def test_preloaded_next_resumes_without_skipping(self):
        self.engine.context = (self.show, ['1', '2', '3'], 2, 7)
        self.engine.position = 0
        self.engine.next_episode_paused = True
        self.assertTrue(self.offered())
        self.assertEqual(self.engine.last_next_offer['label'], 'Start episode')
        self.engine.skip_to_next()
        self.engine.session.command.assert_called_once_with(['set_property', 'pause', False])
        self.engine.start_episode.assert_not_called()
        self.assertFalse(self.offered())

    def test_last_episode_and_closed_player_have_no_offer(self):
        self.engine.context = (self.show, ['1'], 0, 7)
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

    def test_episode_end_waits_for_on_screen_next_offer(self):
        self.event('eof')
        self.event('eof')
        self.engine.start_episode.assert_not_called()
        self.assertTrue(self.engine.episode_ended)
        self.assertFalse(self.engine.next_requested)

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





class ChapterPollingTests(unittest.TestCase):
    def test_vlc_chapter_updates_reach_backend_as_one_property(self):
        from vlc_session import VlcSession
        session = object.__new__(VlcSession)
        session.requested = session.loaded = True
        session.finished = session.caption_requested = False
        session.whisper_only = True
        session.last = {}
        session.caption_text = ''
        session.emit = Mock()
        state = dict(state='playing', input=True, input_state=3,
                     time=800, duration=1200, chapter=4, chapter_count=6, chapter_name='Credits')
        session.poll(state)
        session.emit.assert_any_call({'event': 'property-change', 'name': 'chapter-info',
                                      'data': {'index': 4, 'count': 6, 'name': 'Credits'}})
        session.emit.reset_mock()
        session.poll(state)
        session.emit.assert_not_called()
        session.poll(dict(state, chapter=3))
        session.emit.assert_any_call({'event': 'property-change', 'name': 'chapter-info',
                                      'data': {'index': 3, 'count': 6, 'name': 'Credits'}})


if __name__ == '__main__':
    unittest.main()
