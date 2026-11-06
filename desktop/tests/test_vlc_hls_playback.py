"""Decode HLS transport-stream segments using the installed VLC modules."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(shutil.which('vlc') and shutil.which('ffmpeg'), 'VLC and FFmpeg required')
class HlsPlaybackTests(unittest.TestCase):
    def test_transport_stream_segments_open_and_decode(self):
        with tempfile.TemporaryDirectory(prefix='vlc-hls-check-') as folder:
            playlist = Path(folder) / 'index.m3u8'
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                            'testsrc2=size=160x90:rate=10', '-t', '2', '-an', '-c:v', 'libx264',
                            '-preset', 'ultrafast', '-g', '10', '-f', 'hls', '-hls_time', '1',
                            '-hls_list_size', '0', str(playlist)], check=True, capture_output=True, timeout=15)
            server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=folder))
            server.daemon_threads = True
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result = subprocess.run(['vlc', '--ignore-config', '--intf', 'dummy', '--vout', 'dummy',
                                         '--aout', 'dummy', '--no-audio', '--no-spu', '--no-video-title-show',
                                         '--no-metadata-network-access', '--play-and-exit', '--verbose=2',
                                         f'http://127.0.0.1:{server.server_port}/index.m3u8'],
                                        capture_output=True, text=True, timeout=20)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
            self.assertIn('using demux module "ts"', result.stderr, result.stderr[-3000:])
            self.assertIn('using video decoder module', result.stderr, result.stderr[-3000:])
            self.assertNotIn('Failed to create demuxer', result.stderr)
