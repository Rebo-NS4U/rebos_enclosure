from datetime import datetime, timezone
import unittest
from unittest.mock import patch, Mock
import direct_source
import media_sources
import menu_backend


class SeriesQueueTests(unittest.TestCase):
    def selection(self, videos, episode='1:9', episodes=None):
        show = dict(id='direct:series:tt123', kind='tv', title='Series')
        with patch.object(direct_source, 'metadata', return_value={'videos': videos}):
            return direct_source.playback_selection(show, episodes or [episode], 0,
                    now=datetime(2026, 11, 1, tzinfo=timezone.utc))

    def test_numeric_order_crosses_seasons_and_omits_announced_episodes_and_specials(self):
        videos = [dict(season=s, episode=e, released=date, name=name) for s, e, date, name in [
            (2, 2, '2026-01-02', 'Second'), (1, 10, '2025-01-02', 'Finale'),
            (0, 1, '2025-01-01', 'Special'), (2, 1, '2026-01-01', 'Premiere'),
            (1, 9, '2025-01-01', 'Ninth'), (3, 1, '2027-01-01', 'Announced'),
            (2, 2, '2026-01-02', 'Duplicate'),
        ]]
        show, queue, index = self.selection(videos)
        self.assertEqual(queue, ['1:9', '1:10', '2:1', '2:2'])
        self.assertEqual(index, 0)
        self.assertEqual(show['episodeLabels']['2:1'], 'Season 2 · Episode 1 · Premiere')

    def test_starting_later_season_preserves_exact_selected_episode(self):
        _, queue, index = self.selection([dict(season=1, episode=1), dict(season=2, episode=3)], '2:3')
        self.assertEqual(queue[index], '2:3')
        self.assertEqual(index, 1)

    def test_specials_do_not_jump_into_regular_seasons(self):
        _, queue, _ = self.selection([dict(season=0, episode=1), dict(season=0, episode=2),
                                    dict(season=1, episode=1)], '0:1')
        self.assertEqual(queue, ['0:1', '0:2'])

    def test_missing_metadata_preserves_existing_episode_list(self):
        _, queue, index = self.selection([], '1:9', ['1:9', '1:10'])
        self.assertEqual(queue, ['1:9', '1:10'])
        self.assertEqual(index, 0)

    def test_release_offsets_are_compared_as_instants(self):
        videos = [dict(season=1, episode=9),
                  dict(season=2, episode=1, released='2026-11-01T01:30:00+02:00'),
                  dict(season=2, episode=2, released='2026-10-31T23:30:00-02:00')]
        _, queue, _ = self.selection(videos)
        self.assertEqual(queue, ['1:9', '2:1'])

    def test_anime_and_youtube_keep_their_provider_order(self):
        for kind in ('anime', 'youtube', 'movies'):
            show = dict(id='test', kind=kind)
            with patch.object(direct_source, 'playback_selection') as prepare:
                self.assertEqual(media_sources.playback_selection(show, ['B', 'A'], 0),
                                 (show, ['B', 'A'], 0))
                prepare.assert_not_called()


class QueuePreparationTests(unittest.TestCase):
    def test_pending_automatic_queue_cannot_override_stop_or_disabled_setting(self):
        for cancellation in ('token', 'native_stop', 'disabled'):
            with self.subTest(cancellation=cancellation):
                engine = menu_backend.Engine.__new__(menu_backend.Engine)
                engine.play_token = 7
                engine.session = Mock(stop_count=0)
                engine.settings = {'auto_next': True}
                engine.background = Mock()
                engine.publish_next_episode = Mock()
                show = dict(id='direct:series:tt123', kind='tv', title='Series')
                engine.start_episode(show, ['1:10', '2:1'], 1, 7, automatic=True)
                prepared = engine.background.call_args.args[1]
                engine.start_episode = Mock()
                if cancellation == 'token':
                    engine.play_token += 1
                elif cancellation == 'native_stop':
                    engine.session.stop_count += 1
                else:
                    engine.settings['auto_next'] = False
                prepared((show, ['1:10', '2:1'], 1))
                engine.start_episode.assert_not_called()


if __name__ == '__main__':
    unittest.main()
