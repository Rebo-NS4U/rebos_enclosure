"""Exercise music indexing, persistence and the QML/backend protocol with real audio."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'system/apps/shell/scripts/music_library.py'
spec = importlib.util.spec_from_file_location('music_library', SCRIPT)
music = importlib.util.module_from_spec(spec)
spec.loader.exec_module(music)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg is required')
class MusicLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = dict(HOME=str(self.home), XDG_STATE_HOME=str(self.home/'state'),
                        XDG_CACHE_HOME=str(self.home/'cache'), XDG_CONFIG_HOME=str(self.home/'config'))
        self.patch = patch.dict(os.environ, self.env)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.folder = self.home / 'Music'
        self.folder.mkdir()
        self.song = self.folder / "a 'song' $(safe).flac"
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=220:duration=0.2',
                        '-metadata', 'title=Test song', '-metadata', 'artist=Test artist',
                        '-metadata', 'album=Test album', '-metadata', 'track=3/12', str(self.song)], check=True)
        self.library = music.Library(self.home)

    def test_index_and_cache_invalidation_for_sidecar(self):
        result = self.library.scan()
        self.assertEqual(result['errors'], [])
        track = result['tracks'][0]
        self.assertEqual((track['title'],track['artist'],track['album'],track['number']),
                         ('Test song','Test artist','Test album',3))
        self.assertGreater(track['duration'], 0)
        self.assertEqual(track['url'], self.song.as_uri())
        self.song.with_suffix('.lrc').write_text('[00:00.10]Hello music')
        self.assertEqual(self.library.scan()['tracks'][0]['lyrics'], '[00:00.10]Hello music')
        self.song.unlink()
        self.assertEqual(self.library.scan()['tracks'], [])

    def test_disabled_xdg_music_directory_does_not_scan_home(self):
        config = self.home / 'config'
        config.mkdir()
        (config/'user-dirs.dirs').write_text('XDG_MUSIC_DIR="$HOME"\n')
        library = music.Library(self.home)
        self.assertEqual(library.state['folders'], [str(self.folder)])
        (config/'user-dirs.dirs').write_text('XDG_MUSIC_DIR="$HOME/Audio"\n')
        library = music.Library(self.home)
        self.assertEqual(library.state['folders'], [str(self.home/'Audio')])

    def test_save_preserves_folders_and_reload(self):
        paths = [str(self.song)]
        self.library.dispatch('save', dict(favorites=paths,playlists=[dict(id='1',name='Favorites',paths=paths)]))
        reloaded = music.Library(self.home)
        self.assertEqual(reloaded.state['favorites'], paths)
        self.assertEqual(reloaded.state['playlists'][0]['paths'], paths)
        self.assertEqual(reloaded.state['folders'], [str(self.folder)])
        self.assertFalse((self.library.state_dir/'library.tmp').exists())

    def test_folders_deduplicate_and_report_invalid_audio(self):
        self.library.state['folders'].append(str(self.folder))
        (self.folder/'broken.mp3').write_text('not audio')
        result = self.library.scan()
        self.assertEqual(len(result['tracks']), 1)
        self.assertEqual(len(result['errors']), 1)
        self.assertIn('broken.mp3', result['errors'][0])

    def test_folder_picker_cancel_does_not_change_state(self):
        with patch.object(music.subprocess, 'run', return_value=subprocess.CompletedProcess([],1,'','')):
            self.assertIsNone(self.library.dispatch('folder', {}))
        self.assertEqual(self.library.state['folders'], [str(self.folder)])

    def test_json_line_protocol(self):
        result = subprocess.run([sys.executable,str(SCRIPT)], input=json.dumps(dict(id=1,cmd='scan',args={}))+'\n',
                                capture_output=True,text=True,timeout=30,
                                env={**os.environ,'DBUS_SESSION_BUS_ADDRESS':'unix:path=/nonexistent/music-test'})
        self.assertEqual(result.returncode, 0, result.stderr)
        message = json.loads(result.stdout)
        self.assertTrue(message['ok'], message)
        self.assertEqual(message['id'], 1)
        self.assertEqual(message['data']['tracks'][0]['title'], 'Test song')


if __name__ == '__main__':
    unittest.main()
