import json
import unittest
from unittest.mock import patch

import app
from menu_backend import Engine
from menu_requests import anime_details, anime_season, card_selection


class AnimeSeasonTests(unittest.TestCase):
    def setUp(self):
        self.first = dict(id='example-100', title='Example')
        self.second = dict(id='example-2nd-season-200', title='Example 2nd Season')
        self.group = app.anime_groups([self.second, self.first])[0]

    def test_numbered_and_final_seasons_group_by_title_across_pages(self):
        final = dict(id='example-final-season-300', title='Example: The Final Season Part 2')
        unrelated = dict(id='elsewhere-400', title='Elsewhere: Season 2')
        groups = app.anime_groups([self.group, final, unrelated])
        self.assertEqual([group['title'] for group in groups], ['Example', 'Elsewhere'])
        self.assertEqual(groups[0]['id'], app.anime_series(self.first)['id'])
        self.assertEqual(len(json.loads(groups[0]['seasonEntries'])), 3)

    def test_details_discover_other_seasons_and_resume_existing_history(self):
        first_page = app.anime_series(self.first)
        history = {self.second['id']: {'episode': '2', 'completed': False}}
        with patch.object(app, 'catalogue', return_value=[self.first, self.second]), \
             patch.object(app, 'fetch', return_value=b''), \
             patch.object(app, 'ani_bridge', return_value=['1', '2']) as bridge:
            data = anime_details(first_page, history)
            bridge.assert_called_once_with('episodes', self.second['id'])
        self.assertEqual([season['title'] for season in data['seasons']], ['Season 1', 'Season 2'])
        self.assertEqual(data['seasonId'], self.second['id'])
        self.assertEqual(data['resumeIndex'], 1)

    def test_season_change_and_playback_use_the_season_provider_id(self):
        with patch.object(app, 'ani_bridge', return_value=['1', '2']) as bridge:
            data = anime_season(self.group, self.second['id'], {})
            bridge.assert_called_once_with('episodes', self.second['id'])
        self.assertEqual(data['episodeLabels'][data['episodes'][0]], 'Episode 1')
        settings = dict(mode='sub', quality='best')
        key = Engine.source_key(data['show'], data['episodes'][1], settings)
        self.assertEqual(key, (self.second['id'], '2', 'sub', 'best'))

    def test_quick_play_uses_the_saved_season(self):
        history = {self.group['id']: {'episode': self.second['id'] + ':1', 'completed': True}}
        with patch.object(app, 'ani_bridge', return_value=['1', '2']):
            show, episodes, index = card_selection(self.group, history)
        self.assertEqual(show['id'], self.group['id'])
        self.assertEqual(episodes[index], self.second['id'] + ':2')
