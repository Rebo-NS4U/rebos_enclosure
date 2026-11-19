"""On-demand startup reuses Spotify and gates only live Spotify operations."""
from concurrent.futures import Future
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts'))
import music_spotify
import music_library
import music_mixes


class SpotifyStartupTests(unittest.TestCase):
    def setUp(self):
        hide = patch.object(music_spotify, "hide_window", return_value=True)
        self.hide = hide.start()
        self.addCleanup(hide.stop)

    def test_running_player_is_never_launched_or_raised(self):
        with patch.object(music_spotify, 'running', return_value=True), patch.object(music_spotify.subprocess, 'Popen') as launch:
            music_spotify.ensure_started()
            launch.assert_not_called()
            self.hide.assert_not_called()

    def test_cold_launch_waits_for_player(self):
        with patch.object(music_spotify, 'running', return_value=False) as running, \
                patch.object(music_spotify.shutil, 'which', return_value='/fixture'), \
                patch.object(music_spotify.subprocess, 'Popen') as launch, \
                patch.object(music_spotify.subprocess, 'run') as wait, \
                patch.object(music_spotify.threading, 'Thread') as cleanup:
            music_spotify.ensure_started()
            self.assertEqual(launch.call_args.args[0], ['gtk-launch', 'spotify-launcher'])
            self.assertTrue(launch.call_args.kwargs['start_new_session'])
            self.assertEqual(wait.call_args.args[0],
                             ['gdbus', 'wait', '--session', '--timeout=20', music_spotify.BUS_NAME])
            running.assert_called_once()
            cleanup.assert_called_once_with(target=music_spotify.hide_after_launch, daemon=True)
            cleanup.return_value.start.assert_called_once()
            self.hide.assert_not_called()

    def test_timeout_has_actionable_error(self):
        with patch.object(music_spotify, 'running', return_value=False), \
                patch.object(music_spotify.shutil, 'which', return_value='/fixture'), \
                patch.object(music_spotify.subprocess, 'Popen'), \
                patch.object(music_spotify.subprocess, 'run',
                             side_effect=subprocess.TimeoutExpired('gdbus', 21)):
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


class SuggestedPlaybackTests(unittest.TestCase):
    def test_suggestion_waits_for_spotify_to_confirm_background_playback(self):
        store = music_mixes.Mixes(Path('/unused'), lambda _, default: default, lambda *_: None)
        library = object.__new__(music_library.Library)
        library.mixes = store
        uri = 'spotify:track:' + 'a' * 22
        result = Future()
        wait = result.result

        def confirm(timeout):
            job, pending = store.preview
            self.assertEqual(job['uri'], uri)
            store.update({'preview_id': 'stale'})
            self.assertFalse(pending.done())
            store.update({'preview_id': job['id']})
            return wait(timeout)

        with patch.object(music_spotify, 'running', return_value=True), \
                patch.object(music_mixes, 'Future', return_value=result), \
                patch.object(result, 'result', side_effect=confirm):
            self.assertEqual(library.dispatch('suggestions_play', {'uri': uri})['uri'], uri)
        self.assertIsNone(store.preview)

    def test_missing_confirmation_falls_back_to_native_playback(self):
        store = music_mixes.Mixes(Path('/unused'), lambda _, default: default, lambda *_: None)
        uri = 'spotify:track:' + 'b' * 22

        def play(requested, *, start):
            self.assertEqual(requested, uri)
            self.assertFalse(start)
            self.assertIsNone(store.preview)
            return {'uri': requested}

        with patch.object(music_spotify, 'running', return_value=True), \
                patch.object(Future, 'result', side_effect=TimeoutError), \
                patch('music_preview.preview', side_effect=play) as fallback:
            self.assertEqual(store.play_suggestion(uri), {'uri': uri})
            fallback.assert_called_once_with(uri, start=False)

    def test_closed_spotify_does_not_launch_from_suggested_playback(self):
        store = music_mixes.Mixes(Path('/unused'), lambda _, default: default, lambda *_: None)
        with patch.object(music_spotify, 'running', return_value=False), \
                patch.object(music_spotify.subprocess, 'Popen') as launch:
            with self.assertRaisesRegex(ValueError, 'Open Spotify once'):
                store.play_suggestion('spotify:track:' + 'a' * 22)
            launch.assert_not_called()
        self.assertIsNone(store.preview)


class SpotifyTrayTests(unittest.TestCase):
    def test_only_visible_minimize_action_is_clicked(self):
        from types import SimpleNamespace
        for hidden in (False, True):
            properties = "'label': <'Minimize to Tray'>"
            if hidden:
                properties += ", 'visible': <false>"
            outputs = [
                "(<[':1.99/org/ayatana/NotificationItem/spotify_client']>,)",
                "(<objectpath '/Menu'>,)",
                "(uint32 2, (0, {}, [<(2, {" + properties + "}, @av [])>, <(5, {'label': <'Exit'>}, @av [])>]))",
                "()",
            ]
            with self.subTest(hidden=hidden), patch.object(
                    music_spotify.subprocess, 'run',
                    side_effect=[SimpleNamespace(stdout=value) for value in outputs]) as run:
                self.assertEqual(music_spotify.hide_window(), not hidden)
                self.assertEqual(run.call_count, 3 if hidden else 4)
                if not hidden:
                    self.assertEqual(run.call_args.args[0][-4:],
                                     ['2', 'clicked', '<int32 0>', '0'])

    def test_missing_tray_does_not_break_playback(self):
        with patch.object(music_spotify.subprocess, 'run', side_effect=OSError):
            self.assertFalse(music_spotify.hide_window())


if __name__ == '__main__':
    unittest.main()
