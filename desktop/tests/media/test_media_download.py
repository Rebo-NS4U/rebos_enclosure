"""Exercise download requests against local media without contacting providers."""
from functools import partial
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import Mock, patch

import media_download
import menu_requests


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


class DownloadTests(unittest.TestCase):
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
