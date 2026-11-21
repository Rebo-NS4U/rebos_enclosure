"""Exercise download requests against local media without contacting providers."""
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic, sleep
import unittest
from unittest.mock import Mock, patch

import media_download
import menu_requests


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


class DownloadTests(unittest.TestCase):
    def test_downloads_request_lists_saved_videos_and_ignores_partial_files(self):
        engine = Mock()
        send = Mock()
        with TemporaryDirectory() as directory:
            folder = Path(directory) / 'Rebos Streamer'
            (folder / 'English').mkdir(parents=True)
            (folder / '.download-active').mkdir()
            older = folder / 'Episode 1.mkv'
            newer = folder / 'English' / 'Episode 2 # English.mkv'
            for file in (older, newer, folder / '.download-active' / 'video.mkv', folder / 'notes.txt'):
                file.write_bytes(b'data')
            (folder / 'empty.mkv').touch()
            (folder / 'link.mkv').symlink_to(older)
            os.utime(older, (1, 1))
            with patch.object(media_download.GLib, 'get_user_special_dir', return_value=directory):
                menu_requests.dispatch(dict(action='downloads', request=7, _client='menu'), engine, send)
                work, done, _ = engine.background.call_args.args
                done(work())
            send.assert_called_once_with(dict(event='downloads', request=7, client='menu',
                data=dict(folder=folder.as_uri(), files=[
                    dict(name='English/Episode 2 # English.mkv', url=newer.as_uri()),
                    dict(name='Episode 1.mkv', url=older.as_uri()),
                ])))

    def test_stop_download_cancels_transfer_and_ignores_late_season_callbacks(self):
        engine = Mock(download_active=False, settings={'mode': 'sub', 'quality': '720p'})
        send = Mock()
        show = dict(id='show', kind='tv', title='Example')
        request = dict(action='download_season', show=show, seasonId='2')
        menu_requests.dispatch(request, engine, send)
        engine.background.call_args.args[1]({'episodes': ['2:1', '2:2']})
        key, ready, _ = engine.resolve.call_args.args
        self.assertEqual(key, ('show', '2:1', 'sub', '720p'))
        ready(['video', '', '', ''])
        work, done, failed = engine.background.call_args.args

        with TemporaryDirectory() as directory, ThreadPoolExecutor(1) as pool:
            root = Path(directory)
            marker = root / 'started'
            with patch.object(media_download.GLib, 'get_user_special_dir', return_value=directory), \
                    patch.object(media_download, 'download_stream') as stream:
                def transfer(_links, _kind, path, download):
                    download.run([sys.executable, '-c',
                                  'from pathlib import Path; import sys, time; '
                                  'Path(sys.argv[1]).write_bytes(b"partial"); '
                                  'Path(sys.argv[2]).touch(); time.sleep(30)',
                                  str(path), str(marker)], timeout=5)
                stream.side_effect = transfer
                future = pool.submit(work)
                deadline = monotonic() + 3
                while not marker.exists() and monotonic() < deadline:
                    sleep(0.01)
                self.assertTrue(marker.exists())
                menu_requests.dispatch(dict(action='stop_download'), engine, send)
                with self.assertRaisesRegex(ValueError, 'Download stopped'):
                    future.result(timeout=2)
            self.assertEqual(list((root / 'Rebos Streamer').iterdir()), [])

        menu_requests.dispatch(request, engine, send)
        done('/old-download.mkv')
        failed('Old failure')
        ready(['old', '', '', ''])
        self.assertTrue(engine.download_active)
        engine.resolve.assert_called_once()
        self.assertEqual(engine.background.call_count, 3)
        engine.stop.assert_not_called()
        self.assertEqual(send.call_args_list[-2].args[0], dict(
            event='download', active=False, text='Download stopped.'))

    def test_download_season_queues_selected_season_and_continues_after_failure(self):
        engine = Mock(download_active=False, settings={'mode': 'sub', 'quality': '720p'})
        send = Mock()
        show = dict(id='show', kind='tv', title='Example')
        request = dict(action='download_season', show=show, seasonId='2')
        with patch.object(menu_requests.media_sources, 'season_episodes',
                          return_value={'episodes': ['2:1', '2:2', '2:3']}) as season:
            menu_requests.dispatch(request, engine, send)
            self.assertTrue(engine.download_active)
            work, ready, _ = engine.background.call_args.args
            ready(work())
            season.assert_called_once_with(show, '2')
        engine.resolve.assert_called_once()
        self.assertEqual(engine.resolve.call_args.args[0], ('show', '2:1', 'sub', '720p'))
        menu_requests.dispatch(request, engine, send)
        engine.background.assert_called_once()

        engine.resolve.call_args.args[1](['video', '', '', ''])
        work, done, _ = engine.background.call_args.args
        with patch.object(media_download, 'save', return_value='/download.mkv') as save:
            done(work())
            self.assertEqual(save.call_args.args[0], 'Example · Season 2 · Episode 1')
        self.assertEqual(engine.resolve.call_args.args[0], ('show', '2:2', 'sub', '720p'))
        with patch.object(menu_requests.GLib, 'idle_add', side_effect=lambda callback, *args: callback(*args)):
            engine.resolve.call_args.args[2]('No source')
        self.assertEqual(engine.resolve.call_args.args[0], ('show', '2:3', 'sub', '720p'))
        engine.resolve.call_args.args[1](['video', '', '', ''])
        engine.background.call_args.args[1]('/download.mkv')
        self.assertFalse(engine.download_active)
        engine.stop.assert_not_called()
        self.assertEqual(send.call_args.args[0], dict(
            event='download', active=False, text='Example · Season 2 · Saved 2 of 3 episodes · Failed: 2'))

    def test_download_request_saves_selected_episode_without_touching_playback(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run([
                'ffmpeg', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=s=64x64',
                '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '1',
                '-c:v', 'mpeg2video', '-c:a', 'aac', '-f', 'hls', str(root / 'episode.m3u8'),
            ], check=True)
            with ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=directory)) as server:
                thread = Thread(target=server.serve_forever)
                thread.start()
                try:
                    self.check_download(root, f'http://127.0.0.1:{server.server_port}/episode.m3u8')
                finally:
                    server.shutdown()
                    thread.join()

    def check_download(self, root, source):
        links = [source, '', '', '']
        engine = Mock(download_active=False, settings={'mode': 'dub', 'quality': '720p'})
        engine.media_title.return_value = 'Show / Episode 7'
        engine.resolve.side_effect = lambda _key, ready, _failed: ready(links)
        send = Mock()
        request = dict(action='download', show=dict(id='show', kind='anime'), episode='7')
        with patch.object(media_download.GLib, 'get_user_special_dir', return_value=str(root)):
            menu_requests.dispatch(request, engine, send)
            self.assertTrue(engine.download_active)
            menu_requests.dispatch(request, engine, send)
            engine.background.assert_called_once()
            work, done, _ = engine.background.call_args.args
            done(work())
            duplicate = Path(work())
        engine.resolve.assert_called_once()
        self.assertEqual(engine.resolve.call_args.args[0], ('show', '7', 'dub', '720p'))
        engine.stop.assert_not_called()
        engine.start_episode.assert_not_called()
        self.assertFalse(engine.download_active)
        saved = root / 'Rebos Streamer' / 'Show _ Episode 7.mkv'
        self.assertEqual(send.call_args.args[0], dict(event='download', active=False, text='Saved to ' + str(saved)))
        self.assertEqual(duplicate.name, 'Show _ Episode 7 (2).mkv')
        probe = subprocess.check_output([
            'ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type',
            '-of', 'json', str(saved),
        ], text=True)
        self.assertEqual([track['codec_type'] for track in json.loads(probe)['streams']], ['video', 'audio'])

    def test_failed_transfer_removes_partial_file(self):
        with TemporaryDirectory() as directory:
            def fail(path):
                path.write_bytes(b'partial')
                raise ValueError('Transfer failed')

            with patch.object(media_download.GLib, 'get_user_special_dir', return_value=directory):
                with self.assertRaisesRegex(ValueError, 'Transfer failed'):
                    media_download.save('Episode', fail)
            self.assertEqual(list((Path(directory) / 'Rebos Streamer').iterdir()), [])

    def test_youtube_requests_only_the_selected_video_at_the_configured_quality(self):
        episode = 'https://www.youtube.com/watch?v=example&list=example'
        output = Path('/tmp/Downloads 100%/video.mkv')
        with patch.object(media_download.media_sources, 'ytdlp') as ytdlp:
            media_download.download_youtube(episode, '480p', output)
        args = ytdlp.call_args.args[0]
        self.assertIn('--no-playlist', args)
        self.assertEqual(args[args.index('-f') + 1], 'bv*[height<=480]+ba/b[height<=480]')
        self.assertEqual(args[args.index('-o') + 1], '/tmp/Downloads 100%%/video.%(ext)s')
        self.assertEqual(args[-2:], ['--', episode])
