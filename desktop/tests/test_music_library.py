"""Exercise music indexing, persistence and the QML/backend protocol with real audio."""
import importlib.util
import json
import io
import urllib.error
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
sys.path.insert(0, str(SCRIPT.parent))
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

    def test_sync_membership_preserves_files_and_rescans(self):
        folder = self.folder / 'Synced'
        folder.mkdir()
        kept = folder / ('b'*22 + '.flac')
        removed = folder / ('c'*22 + '.flac')
        shutil.copyfile(self.song, kept)
        shutil.copyfile(self.song, removed)
        metadata = folder / '.enclosure-playlist.json'
        metadata.write_text(json.dumps(dict(sources=['spotify:playlist:'+'a'*22],
            tracks=[dict(uri='spotify:track:'+'b'*22)])))
        for _ in range(2):
            data = self.library.scan()
            playlist = next(p for p in data['state']['playlists'] if p.get('folderPath') == str(folder))
            self.assertEqual(playlist['paths'], [str(kept)])
            self.assertIn(str(removed), [t['path'] for t in data['tracks']])
            self.assertTrue(removed.is_file())
        prepared = self.library.dispatch('playlist_sync', dict(playlist=playlist['id']))
        self.assertTrue(prepared['syncPlaylist'])
        result = self.library.dispatch('playlist_to_spotify', dict(playlist=playlist['id']))
        self.assertTrue(result['pending'])
        self.assertEqual(self.library.mixes.playlist_write['tracks'], ['spotify:track:'+'b'*22])
        self.library.mixes.update(dict(playlist_write_id=self.library.mixes.playlist_write['id']))
        unsafe = self.library.scan()
        target = next(p for p in unsafe['state']['playlists'] if p['id'] == playlist['id'])
        target['paths'].append(str(self.song))
        with patch.object(self.library, 'scan', return_value=unsafe):
            with self.assertRaisesRegex(ValueError, 'identity unknown'):
                self.library.dispatch('playlist_to_spotify', dict(playlist=playlist['id']))
        self.assertIsNone(self.library.mixes.playlist_write)
        metadata.write_text(json.dumps(dict(sources=['spotify:playlist:'+'a'*22], tracks=[])))
        playlist = next(p for p in self.library.scan()['state']['playlists'] if p.get('folderPath') == str(folder))
        self.assertEqual(playlist['paths'], [])
        self.assertTrue(kept.exists() and removed.exists())

    def test_spotify_suggestions_and_download_destination(self):
        uri = 'spotify:track:' + 'b'*22
        other = 'spotify:track:' + 'c'*22
        mix = dict(uri='spotify:playlist:'+'a'*22, name='Daily Mix 1', tracks=[dict(uri=uri, title='Seed', artist='Artist')])
        self.library.mixes.update(dict(mixes=[mix]))
        current = self.library.mixes.dispatch('mixes_get', {})['current'][0]
        target = self.library.dispatch('mixes_download', current)
        folder = Path(target['folder'])
        folder.mkdir(parents=True)
        shutil.copyfile(self.song, folder/('b'*22+'.flac'))
        playlist = self.library.scan()['state']['playlists'][0]
        pending = self.library.dispatch('suggestions_refresh', dict(playlist=playlist['id']))
        self.assertTrue(pending['pending'])
        self.assertEqual(self.library.mixes.suggestion['uri'], mix['uri'])
        job = self.library.mixes.suggestion['id']
        result = dict(suggestion_id=job, tracks=[dict(uri=other, title='New online song', artist='Other artist')])
        self.library.mixes.update(dict(result, suggestion_id='stale'))
        self.assertTrue(self.library.mixes.suggestions()['pending'])
        self.library.mixes.update(result)
        self.assertEqual(self.library.dispatch('suggestions_get', {})['tracks'][0]['uri'], other)
        download = self.library.dispatch('suggestion_download', dict(playlist=playlist['id'], uri=other))
        self.assertEqual(download['folder'], str(folder))
        self.assertEqual(download['links'], 'https://open.spotify.com/track/'+'c'*22)
        with self.assertRaises(ValueError):
            self.library.dispatch('suggestion_download', dict(playlist=playlist['id'], uri=uri))

    def test_downloaded_playlist_source_without_mix_snapshot(self):
        sys.path.insert(0, str(SCRIPT.parent / 'music_downloads'))
        from commands import remember_playlist_source
        folder = self.folder / 'Downloaded playlist'
        folder.mkdir()
        shutil.copyfile(self.song, folder / 'Artist - Named song.flac')
        uri = 'spotify:playlist:' + 'd'*22
        remember_playlist_source(folder, 'https://open.spotify.com/playlist/' + 'd'*22 + '?si=share')
        playlist = self.library.scan()['state']['playlists'][0]
        result = self.library.dispatch('suggestions_refresh', dict(playlist=playlist['id']))
        self.assertTrue(result['pending'])
        self.assertEqual(self.library.mixes.suggestion['uri'], uri)
        self.assertEqual(self.library.mixes.data['current'], [])
        remember_playlist_source(folder, 'https://open.spotify.com/playlist/' + 'e'*22)
        with self.assertRaisesRegex(ValueError, 'source playlist not found'):
            self.library.dispatch('suggestions_refresh', dict(playlist=playlist['id']))

    def test_suggestions_continue_beyond_100_without_duplicates(self):
        mixes = self.library.mixes
        mixes.suggest('local', 'spotify:playlist:' + 'a'*22)
        def batch(start, end):
            return [dict(uri='spotify:track:' + str(i).zfill(22), title=str(i), artist='Artist') for i in range(start, end)]
        mixes.update(dict(suggestion_id=mixes.suggestion['id'], tracks=batch(0, 100)))
        first = mixes.more_suggestions('local')
        self.assertEqual(len(first['tracks']), 100)
        self.assertTrue(first['pending'])
        self.assertEqual(len(mixes.suggestion['skip']), 100)
        job = mixes.suggestion['id']
        mixes.more_suggestions('local')
        self.assertEqual(mixes.suggestion['id'], job)
        mixes.update(dict(suggestion_id='stale', tracks=batch(100, 200)))
        self.assertEqual(len(mixes.suggestions()['tracks']), 100)
        mixes.update(dict(suggestion_id=job, tracks=batch(90, 190)))
        self.assertEqual(len(mixes.suggestions()['tracks']), 190)
        mixes.more_suggestions('local')
        mixes.update(dict(suggestion_id=mixes.suggestion['id'], tracks=batch(90, 100)))
        result = mixes.suggestions()
        self.assertEqual(len(result['tracks']), 190)
        self.assertFalse(result['hasMore'])
        self.assertFalse(mixes.more_suggestions('local')['pending'])
        with self.assertRaises(ValueError):
            mixes.more_suggestions('other')

    def test_playlist_add_survives_rescan_and_reload(self):
        folder = self.folder / 'Downloaded playlist'
        folder.mkdir()
        shutil.copyfile(self.song, folder / 'member.flac')
        playlist = self.library.scan()['state']['playlists'][0]
        args = dict(playlist=playlist['id'], path=str(self.song))
        for _ in range(2):
            result = self.library.dispatch('playlist_add', args)
            updated = next(p for p in result['state']['playlists'] if p['id'] == playlist['id'])
            self.assertEqual(updated['paths'].count(str(self.song)), 1)
        reloaded = music.Library(self.home).scan()
        self.assertIn(str(self.song), reloaded['state']['playlists'][0]['paths'])
        self.library.state['playlists'] = [dict(id='manual', name='Manual', paths=[])]
        self.library.dispatch('playlist_add', dict(playlist='manual', path=str(self.song)))
        self.assertEqual(music.Library(self.home).state['playlists'][0]['paths'], [str(self.song)])
        with self.assertRaises(ValueError):
            self.library.dispatch('playlist_add', dict(playlist=playlist['id'], path='/missing'))

    def test_mix_download_links_and_local_playback_identity(self):
        mix = dict(uri='spotify:playlist:'+'a'*22, name='Daily Mix 1', tracks=[
            dict(uri='spotify:track:'+'b'*22, title='Test song', artist='Test artist'),
            dict(uri='spotify:track:'+'c'*22, title='Second song', artist='Test artist')])
        self.library.mixes.update(dict(mixes=[mix]))
        current = self.library.mixes.dispatch('mixes_get', {})['current'][0]
        args = dict(uri=current['uri'], version=current['version'])
        download = self.library.dispatch('mixes_download', args)
        self.assertEqual(download['links'], 'https://open.spotify.com/playlist/'+'a'*22)
        self.assertEqual(len(download['links'].split()), 1)
        folder = Path(download['folder'])
        self.assertTrue(folder.is_relative_to(self.folder/'Daily Mixes'))
        folder.mkdir(parents=True)
        song = folder/('b'*22+'.flac')
        shutil.copyfile(self.song, song)
        indexed = next(t for t in self.library.scan()['tracks'] if t['path'] == str(song))
        self.assertEqual(indexed['spotifyUri'], mix['tracks'][0]['uri'])
        self.assertEqual(indexed['url'], song.as_uri())
        self.library.dispatch('mixes_save', args)
        mix['tracks'][0]['title'] = 'New version'
        self.library.mixes.update(dict(mixes=[mix]))
        self.assertEqual(self.library.dispatch('mixes_download', args), download)
        with self.assertRaises(ValueError):
            self.library.dispatch('mixes_download', dict(uri=current['uri'], version='missing'))

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

    def test_folder_playlists_refresh_without_changing_saved_playlists(self):
        folder = self.folder / 'Road trip'
        nested = folder / 'Disc 1'
        nested.mkdir(parents=True)
        song = nested / 'track.flac'
        shutil.copyfile(self.song, song)
        (self.folder / 'Empty').mkdir()
        manual = dict(id='manual', name='My mix', paths=[str(self.song)])
        self.library.dispatch('save', dict(playlists=[manual]))
        playlists = self.library.scan()['state']['playlists']
        self.assertEqual([p['name'] for p in playlists], ['My mix', 'Road trip'])
        generated = playlists[1]
        self.assertTrue(generated['folder'])
        self.assertEqual(generated['paths'], [str(song)])
        self.assertEqual(self.library.scan()['state']['playlists'][1]['id'], generated['id'])
        self.library.dispatch('save', dict(playlists=playlists))
        self.assertEqual(music.Library(self.home).state['playlists'], [manual])
        renamed = nested / 'renamed.flac'
        song.rename(renamed)
        self.assertEqual(self.library.scan()['state']['playlists'][1]['paths'], [str(renamed)])
        renamed.unlink()
        self.assertEqual(self.library.scan()['state']['playlists'], [manual])

    def test_daily_mixes_are_separate_playlists(self):
        first = self.folder / 'Daily Mixes' / 'Daily Mix 1-aaaaaaaaaaaa'
        second = self.folder / 'Daily Mixes' / 'Daily Mix 2-bbbbbbbbbbbb'
        for folder in (first, second):
            folder.mkdir(parents=True)
            shutil.copyfile(self.song, folder / 'track.flac')
        playlists = self.library.scan()['state']['playlists']
        self.assertEqual([p['name'] for p in playlists], ['Test artist Mix · Daily Mix 1', 'Test artist Mix · Daily Mix 2'])
        self.assertTrue(all(p['mix'] for p in playlists))
        self.assertEqual([p['sourceName'] for p in playlists], ['Daily Mix 1', 'Daily Mix 2'])
        self.assertEqual(playlists[0]['paths'], [str(first / 'track.flac')])
        self.assertEqual(playlists[1]['paths'], [str(second / 'track.flac')])
        stable_id = playlists[0]['id']
        (second / 'track.flac').unlink()
        playlists = self.library.scan()['state']['playlists']
        self.assertEqual(len(playlists), 1)
        self.assertEqual(playlists[0]['id'], stable_id)
        self.assertEqual(playlists[0]['name'], 'Test artist Mix')

    def test_mix_names_use_leading_artists_and_clean_fallback(self):
        folder = self.folder / 'Daily Mixes' / 'Daily Mix 3-cccccccccccc'
        folder.mkdir(parents=True)
        artists = ['Radiohead', 'Muse', 'Radiohead', 'Other']
        for index in range(len(artists)):
            shutil.copyfile(self.song, folder / f'{index}.flac')
        inspect = self.library.inspect
        def metadata(path):
            track = dict(inspect(path))
            if path.parent == folder:
                track['artist'] = artists[int(path.stem)]
            return track
        with patch.object(self.library, 'inspect', side_effect=metadata):
            playlist = self.library.scan()['state']['playlists'][0]
            self.assertEqual(playlist['name'], 'Radiohead · Muse Mix')
            self.assertEqual(playlist['sourceName'], 'Daily Mix 3')
            artists[:] = ['Unknown artist'] * len(artists)
            self.assertEqual(self.library.scan()['state']['playlists'][0]['name'], 'Daily Mix 3')

    def test_automatic_lyrics_prefer_synced_and_cache_offline(self):
        track = dict(title='Song', artist='Artist', album='Album', duration=120)
        response = io.BytesIO(json.dumps(dict(syncedLyrics='[00:01]Hello', plainLyrics='Hello')).encode())
        with patch.object(music.urllib.request, 'urlopen', return_value=response) as fetch:
            self.assertEqual(self.library.lyrics(track)['text'], '[00:01]Hello')
            self.assertEqual(self.library.lyrics(track)['text'], '[00:01]Hello')
            self.assertEqual(fetch.call_count, 1)
            self.assertIn('track_name=Song', fetch.call_args.args[0].full_url)
            self.assertEqual(fetch.call_args.kwargs['timeout'], 8)

    def test_lyrics_search_rejects_wrong_recording(self):
        track = dict(title='Song', artist='Artist', duration=120)
        records = [dict(trackName='Song', artistName='Other', duration=120, syncedLyrics='Wrong'),
                   dict(trackName='Song', artistName='Artist', duration=200, syncedLyrics='Wrong'),
                   dict(trackName='Song', artistName='Artist', duration=121, plainLyrics='Right')]
        missing = urllib.error.HTTPError('https://lrclib.net', 404, 'Missing', {}, None)
        with patch.object(music.urllib.request, 'urlopen', side_effect=[missing,
                io.BytesIO(json.dumps(records).encode())]):
            self.assertEqual(self.library.lyrics(track)['text'], 'Right')

    def test_lyrics_embedded_priority_and_network_failure(self):
        with patch.object(music.urllib.request, 'urlopen', side_effect=OSError('offline')) as fetch:
            self.assertEqual(self.library.lyrics(dict(lyrics='Embedded'))['text'], 'Embedded')
            fetch.assert_not_called()
            result = self.library.lyrics(dict(title='Song', artist='Artist'))
            self.assertEqual(result['text'], '')
            self.assertIn('online', result['status'])
            self.assertEqual(list(self.library.cache_dir.glob('lyrics-*.json')), [])

    def test_embedded_ogg_lyrics_and_stream_metadata(self):
        song = self.folder / 'embedded.ogg'
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(self.song),
                        '-metadata', 'lyrics=Embedded lyrics', str(song)], check=True)
        track = self.library.inspect(song)
        self.assertEqual(track['lyrics'], 'Embedded lyrics')
        self.assertEqual(track['title'], 'Test song')

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
