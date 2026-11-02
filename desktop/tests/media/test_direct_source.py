import contextlib
import json
import unittest
import functools
import http.server
from pathlib import Path
import subprocess
import tempfile
import threading
from unittest.mock import Mock, patch
import direct_source as source
import media_sources
from media_validation import InvalidMedia


class HTTPSOnlyTests(unittest.TestCase):
    def test_movie_details_keep_full_synopsis_and_structured_credits(self):
        description = 'A complete plot description. ' * 200
        meta = dict(name='Example', description=description, cast=['Actor One', 'Actor Two', 'Actor One'],
                    director=['Director'], genres=['Drama', 'Comedy'], releaseInfo='2024',
                    runtime='123 min', imdbRating='8.2', country='United States', released='2024-05-10T00:00:00Z')
        with patch.object(source, 'metadata', return_value=meta):
            data = source.details(dict(id='direct:movie:tt1', kind='movies'))
        self.assertEqual(data['description'], description)
        self.assertEqual(data['cast'], ['Actor One', 'Actor Two'])
        self.assertEqual(data['directors'], ['Director'])
        self.assertEqual(data['genres'], ['Drama', 'Comedy'])
        self.assertEqual(data['released'], '2024-05-10')
        self.assertEqual(data['episodes'], ['movie'])

    def test_optional_credits_are_safe_for_missing_or_scalar_metadata(self):
        for meta in ({}, dict(cast='Actor', director='Director', genres=None)):
            with patch.object(source, 'metadata', return_value=meta):
                data = source.details(dict(id='direct:movie:tt1', kind='movies'))
            self.assertIsInstance(data['cast'], list)
            self.assertIsInstance(data['directors'], list)
            self.assertEqual(data['genres'], [])

    def setUp(self):
        # Regression tests never consume a real connected account.
        self.account = patch('torbox_source.read_key', return_value='')
        self.account.start()
        self.addCleanup(self.account.stop)

    def stream(self, **extra):
        return dict(url='https://cdn.example/video', name='English 720p WEB-DL', **extra)

    def test_torrent_browser_and_non_https_resources_are_rejected(self):
        for change in [dict(url='magnet:?xt=urn:btih:123'), dict(infoHash='123'),
                       dict(externalUrl='https://example.com/watch'), dict(ytId='123'),
                       dict(url='http://cdn.example/video'), dict(url='file:///tmp/video'),
                       dict(behaviorHints={'p2p': True}), dict(type='torrent')]:
            self.assertFalse(source.eligible(dict(self.stream(), **change)), change)
        self.assertTrue(source.eligible(self.stream()))

    def test_english_and_cam_checks_apply_to_each_release(self):
        for label in ('Hindi 1080p', '1080p WEB-DL', 'English HDCAM', 'English CAM', 'ENG HDTS'):
            self.assertFalse(source.eligible(dict(self.stream(), name=label)))
        self.assertTrue(source.eligible(dict(self.stream(), name='English Dub 720p')))

    def probe(self, duration=1320, language='eng', decode=0, height=720):
        stack = contextlib.ExitStack()
        stack.enter_context(patch.object(source.stream_relay, 'register', return_value='http://127.0.0.1:1234/media/1'))
        data = dict(format={'duration': duration}, streams=[dict(index=0, codec_type='video', height=height), dict(index=1, codec_type='audio', tags={'language': language})])
        run = stack.enter_context(patch.object(source.subprocess, 'run', side_effect=[Mock(returncode=0, stdout=json.dumps(data)), Mock(returncode=decode)]))
        return stack, run

    def test_unknown_runtime_still_rejects_short_preview(self):
        stack, run = self.probe(duration=23)
        with stack, self.assertRaises(InvalidMedia):
            source.verify(self.stream(), 0, 'best')
        self.assertEqual(run.call_count, 1)

    def test_conflicting_foreign_audio_tag_is_rejected(self):
        stack, _ = self.probe(language='hin')
        with stack, self.assertRaises(InvalidMedia):
            source.verify(self.stream(), 1320, 'best')

    def test_mislabeled_4k_source_is_rejected_at_1080p(self):
        stack, run = self.probe(height=2160)
        with stack, self.assertRaisesRegex(InvalidMedia, 'selected playback quality'):
            source.verify(self.stream(), 1320, '1080p')
        self.assertEqual(run.call_count, 1)

    def test_direct_quality_limit_does_not_try_4k_as_fallback(self):
        row = dict(self.stream(), name='English 2160p WEB-DL')
        with patch.object(source, 'streams', return_value=[row]), patch.object(source, 'metadata', return_value={'runtime': '22 min'}), patch.object(source, 'verify') as verify:
            with self.assertRaises(InvalidMedia):
                source.resolve('direct:series:tt0386676', '1:7', '1080p')
        verify.assert_not_called()

    def test_verified_stream_requires_actual_mid_video_decode(self):
        stack, run = self.probe()
        with stack:
            links = source.verify(self.stream(), 1320, '720p')
        self.assertEqual(links.audio_map, '0:1')
        self.assertIn('600', run.call_args_list[1].args[0])
        stack, _ = self.probe(decode=1)
        with stack, self.assertRaisesRegex(InvalidMedia, 'mid-video'):
            source.verify(self.stream(), 1320, 'best')

    def test_verified_chapter_times_are_retained_for_advance_preparation(self):
        stack, run = self.probe()
        data = dict(format={'duration': 1320}, streams=[dict(index=0, codec_type='video'),
                    dict(index=1, codec_type='audio', tags={'language': 'eng'})],
                    chapters=[dict(start_time='1200', tags={'title': 'Credits'})])
        run.side_effect = [Mock(returncode=0, stdout=json.dumps(data)), Mock(returncode=0)]
        with stack:
            links = source.verify(self.stream(), 1320, '1080p')
        self.assertEqual(links.chapters, data['chapters'])

    def test_movie_routes_never_call_the_browser_resolver(self):
        with patch.object(source, 'resolve', return_value=['https://cdn.example/video','','','']) as resolve, patch('primewire_source.resolve') as browser:
            for show in ('direct:movie:tt0111161', 'primewire:movie:278', 'moviebox:123'):
                media_sources.resolve_movie(show, 'movie', 'best')
            self.assertEqual(resolve.call_count, 3)
            browser.assert_not_called()

    def test_failed_candidate_tries_another_https_stream(self):
        with patch.object(source, 'streams', return_value=[self.stream(),self.stream()]), patch.object(source, 'metadata', return_value={'runtime':'22 min'}), patch.object(source, 'verify', side_effect=[InvalidMedia('failed'), ['verified']]) as verify:
            self.assertEqual(source.resolve('direct:series:tt0386676','1:1','best'), ['verified'])
            self.assertEqual(verify.call_count, 2)

    def test_history_does_not_depend_on_current_source_availability(self):
        show=dict(id='direct:movie:tt0111161',kind='movies',title='Movie')
        with patch.object(source,'streams',side_effect=RuntimeError('down')) as request:
            self.assertEqual(source.filter_history([show,show]),[show])
            request.assert_not_called()

    def test_real_full_hls_has_english_audio_and_decodes_after_seeking(self):
        self.check_real_container('m3u8')

    def test_real_matroska_decodes_without_hls_only_options(self):
        self.check_real_container('mkv')

    def test_real_mp4_retains_container_for_player_demux_selection(self):
        self.check_real_container('mp4')

    def check_real_container(self, extension):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / ('video.' + extension)
            options = ['-f','hls','-hls_time','12','-hls_list_size','0'] if extension == 'm3u8' else []
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=s=16x16:d=132:r=1','-f','lavfi','-i','anullsrc=r=8000:cl=mono','-t','132','-c:v','libx264','-g','12','-c:a','aac','-metadata:s:a:0','language=eng',*options,str(target)], check=True, capture_output=True, timeout=15)
            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *args): pass
            server = http.server.ThreadingHTTPServer(('127.0.0.1',0), functools.partial(Handler,directory=folder))
            threading.Thread(target=server.serve_forever,daemon=True).start()
            relay = source.stream_relay.StreamRelay(allow_local=True)
            try:
                local = relay.register(f'http://127.0.0.1:{server.server_port}/video.' + extension)
                with patch.object(source.stream_relay,'register',return_value=local):
                    links = source.verify(self.stream(),132,'720p')
                self.assertEqual(links[0],local)
                self.assertEqual(links.audio_map,'0:1')
                self.assertEqual(links.is_hls, extension == 'm3u8')
                self.assertEqual('mov' in links.format_name.split(','), extension == 'mp4')
            finally:
                relay.close()
                server.shutdown()
                server.server_close()
