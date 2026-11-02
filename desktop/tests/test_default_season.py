"""Season defaults must match the regular episodes checked by catalogue labels."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'payload/home/code/anime-streamer'))
import direct_source

class DefaultSeasonTests(unittest.TestCase):
    def details(self, saved=None, specials_only=False):
        videos = [dict(season=0, episode=1, name='Behind the scenes')]
        if not specials_only:
            videos += [dict(season=1, episode=1, name='Premiere'), dict(season=2, episode=1)]
        with patch.object(direct_source, 'metadata', return_value=dict(videos=videos)):
            return direct_source.details(dict(id='direct:series:tt33043892', kind='tv'), saved)

    def test_new_show_starts_with_regular_episodes(self):
        data = self.details()
        self.assertEqual(data['seasonId'], '1')
        self.assertEqual(data['episodes'], ['1:1'])
        self.assertEqual(data['seasons'][0]['title'], 'Specials')

    def test_saved_season_is_preserved_including_specials(self):
        for saved in ('0:1', '2:1'):
            self.assertEqual(self.details(saved)['seasonId'], saved.split(':')[0])

    def test_specials_only_show_still_lists_episodes(self):
        self.assertEqual(self.details(specials_only=True)['episodes'], ['0:1'])
