from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import menu_backend


class EpisodePrefetchTests(unittest.TestCase):
    def setUp(self):
        self.engine = menu_backend.Engine.__new__(menu_backend.Engine)
        self.engine.context = (dict(id='direct:series:tt123', kind='tv', title='Series'), ['1:7', '1:8'], 0, 7)
        self.engine.play_token = 7
        self.engine.file_loaded = True
        self.engine.paused = self.engine.next_episode_paused = self.engine.next_requested = False
        self.engine.duration = 2738.945
        self.engine.position = 2524.375
        self.engine.links = SimpleNamespace(chapters=[dict(start_time='2644.375', tags={'title': 'Credits'})])
        self.engine.settings = dict(mode='dub', quality='1080p', auto_next=False)
        self.engine.prefetch_key = None
        self.engine.prefetch_retry_at = 0
        self.engine.resolved, self.engine.resolving = {}, {}
        self.engine.background = Mock()
        self.key = ('direct:series:tt123', '1:8', 'dub', '1080p')
        self.clock = patch.object(menu_backend.time, 'monotonic', return_value=1000).start()
        self.addCleanup(patch.stopall)

    def test_prepares_two_minutes_before_credits_and_foreground_reuses_result(self):
        self.engine.position -= .01
        self.engine.prefetch_next()
        self.engine.background.assert_not_called()
        self.engine.position += .01
        self.engine.prefetch_next()
        self.engine.background.assert_called_once()
        self.engine.prefetch_next()
        self.engine.background.assert_called_once()
        prepared = ['private-loopback-media', '', '', '']
        self.engine.background.call_args.args[1](prepared)
        done, failed = Mock(), Mock()
        self.engine.resolve(self.key, done, failed)
        done.assert_called_once_with(prepared)
        failed.assert_not_called()
        self.engine.background.assert_called_once()

    def test_tv_anime_and_youtube_are_prepared_without_changing_current_episode(self):
        for kind, sid in [('tv', 'direct:series:tt123'), ('anime', 'anime-show'), ('youtube', 'youtube:playlist')]:
            self.engine.context = (dict(id=sid, kind=kind), ['one', 'two'], 0, 7)
            self.engine.prefetch_key = None
            self.engine.resolving = {}
            self.engine.background.reset_mock()
            self.engine.prefetch_next()
            self.engine.background.assert_called_once()
            self.assertEqual(self.engine.context[2], 0)

    def test_failure_is_throttled_and_can_retry(self):
        self.engine.prefetch_next()
        self.engine.background.call_args.args[2]('Source temporarily unavailable')
        self.engine.prefetch_next()
        self.engine.background.assert_called_once()
        self.clock.return_value += 31
        self.engine.prefetch_next()
        self.assertEqual(self.engine.background.call_count, 2)

    def test_background_worker_buffers_registered_startup_bytes(self):
        from primewire_source import PlaybackLinks
        links = PlaybackLinks('https://video.example/next.mkv', 1)
        links.chapters = [{'start_time': '2644', 'tags': {'title': 'Credits'}}]
        self.engine.prefetch_next()
        worker = self.engine.background.call_args.args[0]
        with patch.object(menu_backend.media_sources, 'resolve_movie', return_value=links), \
             patch.object(menu_backend.stream_relay, 'register', return_value='http://127.0.0.1:1234/media/next'), \
             patch.object(menu_backend.stream_relay, 'preload', return_value=True) as buffer:
            prepared = worker()
        self.assertIs(prepared, links)
        self.assertEqual(prepared[0], 'http://127.0.0.1:1234/media/next')
        self.assertEqual(prepared.chapters, links.chapters)
        buffer.assert_called_once_with(prepared[0])

    def test_expired_preparation_is_refreshed_after_long_credits_or_pause(self):
        self.engine.resolved[self.key] = (701, ['prepared'])
        self.engine.prefetch_next()
        self.engine.background.assert_not_called()
        self.clock.return_value += 2
        self.engine.prefetch_next()
        self.engine.background.assert_called_once()

    def test_quality_changes_prepare_the_new_selection(self):
        self.engine.prefetch_next()
        self.engine.settings['quality'] = '720p'
        self.engine.prefetch_next()
        self.assertIn(('direct:series:tt123', '1:8', 'dub', '720p'), self.engine.resolving)

    def test_paused_stopped_preloaded_final_and_movies_do_not_prepare(self):
        for field in ('paused', 'next_episode_paused', 'next_requested'):
            setattr(self.engine, field, True)
            self.engine.prefetch_next()
            setattr(self.engine, field, False)
        self.engine.play_token += 1
        self.engine.prefetch_next()
        self.engine.play_token -= 1
        self.engine.context = (dict(id='movie', kind='movies'), ['one', 'two'], 0, 7)
        self.engine.prefetch_next()
        self.engine.context = (dict(id='show', kind='tv'), ['one'], 0, 7)
        self.engine.prefetch_next()
        self.engine.background.assert_not_called()

    def test_intro_and_malformed_chapters_do_not_move_the_offer_earlier(self):
        self.assertEqual(menu_backend.next_offer_start(1200, [dict(start_time=60, title='Opening Credits'),
                        dict(start_time='bad', title='Credits')]), 1110)


if __name__ == '__main__':
    unittest.main()
