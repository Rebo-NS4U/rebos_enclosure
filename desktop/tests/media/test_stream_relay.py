import http.server
import json
import re
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from http.client import IncompleteRead
from unittest.mock import MagicMock, patch
from urllib.request import urlopen, Request
from stream_relay import StreamRelay


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.path=Path(self.folder.name)
        folder=self.folder.name
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self,*args,**kwargs): super().__init__(*args,directory=folder,**kwargs)
            def log_message(self,*args): pass
            def do_GET(self):
                self.server.last_range = self.headers.get('Range')
                if self.path.startswith('/ranged'):
                    self.server.ranges.append(self.headers.get('Range'))
                    data = Path(folder, self.path.lstrip('/')).read_bytes()
                    match = re.fullmatch(r'bytes=(\d+)-(\d*)', self.headers.get('Range', ''))
                    start = int(match[1]) if match else 0
                    end = min(int(match[2]), len(data) - 1) if match and match[2] else len(data) - 1
                    self.send_response(206 if match else 200)
                    self.send_header('Content-Type', 'video/mp4')
                    self.send_header('Content-Length', str(end - start + 1))
                    self.send_header('ETag', '"test-video"')
                    if match: self.send_header('Content-Range', f'bytes {start}-{end}/{len(data)}')
                    self.end_headers()
                    self.wfile.write(data[start:end + 1])
                    return
                super().do_GET()
        self.origin=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.origin.ranges = []
        threading.Thread(target=self.origin.serve_forever,daemon=True).start()
        self.base=f'http://127.0.0.1:{self.origin.server_port}/'
        self.relay=StreamRelay(allow_local=True)

    def tearDown(self):
        self.relay.close();self.origin.shutdown();self.origin.server_close();self.folder.cleanup()

    def test_open_ended_byte_range_is_forwarded_without_truncation(self):
        self.path.joinpath('video').write_bytes(b'video')
        local = self.relay.register(self.base + 'video')
        with urlopen(Request(local, headers={'Range': 'bytes=0-'})) as response:
            self.assertEqual(response.read(), b'video')
        self.assertEqual(self.origin.last_range, 'bytes=0-')

    def test_preloaded_prefix_is_reused_and_stitched_to_remaining_video(self):
        data = bytes(range(256)) * 1000
        self.path.joinpath('rangedvideo').write_bytes(data)
        local = self.relay.register(self.base + 'rangedvideo')
        self.assertTrue(self.relay.preload(local, size=65536))
        with urlopen(Request(local, headers={'Range': 'bytes=0-'})) as response:
            self.assertEqual(response.read(), data)
            self.assertEqual(response.headers['Content-Range'], f'bytes 0-{len(data)-1}/{len(data)}')
        self.assertEqual(self.origin.ranges, ['bytes=0-65535', f'bytes=65536-{len(data)-1}'])
        with urlopen(Request(local, headers={'Range': 'bytes=100-199'})) as response:
            self.assertEqual(response.read(), data[100:200])
        self.assertEqual(len(self.origin.ranges), 2)
        self.assertEqual(self.relay.preload_hits, 2)

    def test_expired_prefix_and_seeks_outside_prefix_use_normal_upstream(self):
        data = bytes(range(256)) * 1000
        self.path.joinpath('rangedvideo').write_bytes(data)
        local = self.relay.register(self.base + 'rangedvideo')
        self.assertTrue(self.relay.preload(local, size=65536))
        with urlopen(Request(local, headers={'Range': 'bytes=100000-100099'})) as response:
            self.assertEqual(response.read(), data[100000:100100])
        with patch('stream_relay.time.monotonic', return_value=10**20):
            with urlopen(Request(local, headers={'Range': 'bytes=0-99'})) as response:
                self.assertEqual(response.read(), data[:100])
        self.assertEqual(self.relay.preload_hits, 0)

    def test_preload_rejects_playlist_and_unregistered_routes(self):
        self.path.joinpath('track').write_text('#EXTM3U\n#EXT-X-ENDLIST\n')
        self.assertFalse(self.relay.preload(self.relay.register(self.base + 'track')))
        self.assertFalse(self.relay.preload(self.base + 'rangedvideo'))

    def test_midstream_failure_does_not_append_http_error_to_video(self):
        local = self.relay.register(self.base + 'interrupted')
        upstream = MagicMock()
        upstream.__enter__.return_value = upstream
        upstream.url = self.base + 'interrupted'
        upstream.status = 200
        upstream.headers = {'Content-Type': 'video/mp4', 'Content-Length': '100000'}
        upstream.read.side_effect = [b'v' * 64, b'v' * 65536, OSError('upstream timeout')]
        with patch.object(self.relay.opener, 'open', return_value=upstream):
            with urlopen(local) as response:
                with self.assertRaises(IncompleteRead) as error:
                    response.read()
        self.assertEqual(error.exception.partial, b'v' * 65600)

    def test_native_vlc_mp4_buffers_seeks_and_resumes_through_relay(self):
        from vlc_session import VlcSession
        from primewire_source import PlaybackLinks
        target = self.path / 'rangedvideo.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'testsrc2=s=64x64:d=8:r=10', '-c:v', 'libx264',
                        '-movflags', '+faststart', str(target)], check=True, capture_output=True)
        links = PlaybackLinks(self.relay.register(self.base + 'rangedvideo.mp4'), 0)
        links.format_name = 'mov,mp4,m4a,3gp,3g2,mj2'
        self.assertTrue(self.relay.preload(links[0], size=4096))
        session = VlcSession({'audio_normalization': False}, lambda event: None,
                             self.path / 'vlc.log',
                             extra_args=['-I', 'dummy', '--aout=dummy', '--vout=dummy'])
        def wait_for(predicate):
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                if predicate():
                    return
                time.sleep(.05)
            self.fail('VLC MP4 playback did not reach the expected state: ' +
                      repr(session.last_state))
        try:
            session.load(links, 'MP4 network playback test', paused=True)
            wait_for(lambda: session.loaded and session.last_state.get('state') == 'paused')
            session.command(['seek', 3])
            wait_for(lambda: session.last_state.get('time', 0) >= 2.8)
            session.command(['set_property', 'pause', False])
            wait_for(lambda: session.last_state.get('time', 0) >= 4)
            log = (self.path / 'vlc.log').read_text(errors='replace')
            self.assertIn('using demux module "avformat"', log)
            self.assertGreater(self.relay.preload_hits, 0)
        finally:
            session.close()
            session.process.wait(timeout=5)

    def test_nested_playlists_keys_and_cross_origin_credentials(self):
        self.path.joinpath('track').write_text('#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key"\n#EXTINF:5,\nchunk\n#EXT-X-ENDLIST\n')
        self.path.joinpath('key').write_bytes(b'0123456789abcdef')
        self.path.joinpath('chunk').write_bytes(b'media')
        local=self.relay.register(self.base+'track',{'Cookie':'private=value'})
        with urlopen(local) as response: rewritten=response.read().decode()
        self.assertNotIn(self.base,rewritten)
        self.assertNotIn('private=value',rewritten)
        self.assertIn('http://127.0.0.1:',rewritten)
        other=self.relay.rewrite('#EXTM3U\nhttps://other.example/segment\n',self.base+'master',{'Cookie':'private=value','Authorization':'private','Referer':'https://primewire.mov/'})
        path='/' + other.splitlines()[1].split('/',3)[3]
        _,headers,_=self.relay.sources[path]
        self.assertNotIn('Cookie',headers);self.assertNotIn('Authorization',headers)

    def test_quality_filters_video_variants_but_keeps_audio(self):
        master='#EXTM3U\n#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",LANGUAGE="en",URI="audio"\n#EXT-X-STREAM-INF:BANDWIDTH=1,RESOLUTION=1280x720,AUDIO="audio"\nvideo720\n#EXT-X-STREAM-INF:BANDWIDTH=2,RESOLUTION=1920x1080,AUDIO="audio"\nvideo1080\n'
        rewritten=self.relay.rewrite(master,self.base+'master',{},720)
        self.assertIn('LANGUAGE="en"',rewritten)
        self.assertIn('1280x720',rewritten);self.assertNotIn('1920x1080',rewritten)

    def test_actual_hls_decodes_and_seeks_through_extensionless_proxy_routes(self):
        target=self.path/'master.m3u8'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=s=32x32:d=8:r=10','-c:v','libx264','-g','10','-f','hls','-hls_time','2','-hls_list_size','0',str(target)],check=True,capture_output=True)
        local=self.relay.register(self.base+'master.m3u8')
        result=subprocess.run(['ffmpeg','-v','error','-allowed_extensions','ALL','-allowed_segment_extensions','ALL','-extension_picky','0','-ss','5','-i',local,'-frames:v','1','-f','null','-'],capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
