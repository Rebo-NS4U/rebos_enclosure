"""On-demand startup reuses Spotify and gates only live Spotify operations."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts'))
import music_spotify
import music_library


class SpotifyStartupTests(unittest.TestCase):
    def test_running_player_is_never_launched_or_raised(self):
        with patch.object(music_spotify, 'running', return_value=True), patch.object(music_spotify.subprocess, 'Popen') as launch:
            music_spotify.ensure_started()
            launch.assert_not_called()

    def test_cold_launch_waits_for_player(self):
        with patch.object(music_spotify, 'running', side_effect=[False, False, True]), patch.object(music_spotify.shutil, 'which', return_value='/fixture'), patch.object(music_spotify.subprocess, 'Popen') as launch, patch.object(music_spotify.time, 'sleep') as sleep:
            music_spotify.ensure_started()
            self.assertEqual(launch.call_args.args[0], ['gtk-launch', 'spotify-launcher'])
            self.assertTrue(launch.call_args.kwargs['start_new_session'])
            sleep.assert_called_once()

    def test_timeout_has_actionable_error(self):
        with patch.object(music_spotify, 'running', return_value=False), patch.object(music_spotify.shutil, 'which', return_value='/fixture'), patch.object(music_spotify.subprocess, 'Popen'), patch.object(music_spotify.time, 'monotonic', side_effect=[0, 21]):
            with self.assertRaisesRegex(ValueError, 'sign in'):
                music_spotify.ensure_started()

    def test_only_live_requests_start_spotify(self):
        library = object.__new__(music_library.Library)
        class Mixes:
            def dispatch(self, cmd, args):
                return cmd
        library.mixes = Mixes()
        with patch.object(music_spotify, 'ensure_started') as start:
            for cmd in ('mixes_get', 'mixes_save'):
                self.assertEqual(library.dispatch(cmd, {}), cmd)
            start.assert_not_called()
            for cmd in ('mixes_load', 'mixes_refresh'):
                self.assertEqual(library.dispatch(cmd, {}), cmd)
            self.assertEqual(start.call_count, 2)

    def test_opening_music_does_not_launch_spotify(self):
        script = Path(music_library.__file__).with_name('open_music.sh').read_text()
        self.assertNotIn('spotify', script.lower())


if __name__ == '__main__':
    unittest.main()
