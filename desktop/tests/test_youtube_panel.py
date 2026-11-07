"""Account feed, playback queue, and YouTube auto-next behavior."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'system/apps/media'))
import media_sources
import youtube_account
import menu_backend


class YouTubePanelTests(unittest.TestCase):
    def test_resolution_checks_direct_streams_and_preserves_quality_audio_and_captions(self):
        payload = {'requested_formats': [
            {'vcodec': 'h264', 'url': 'https://example.com/video'},
            {'vcodec': 'none', 'url': 'https://example.com/audio'}],
            'subtitles': {'en': [{'ext': 'vtt', 'url': 'https://example.com/subs'}]}}
        with patch.object(media_sources, 'ytdlp', return_value=json.dumps(payload)) as extract:
            links = media_sources.resolve_youtube('https://www.youtube.com/watch?v=test', '720p')
        self.assertEqual(links, ['https://example.com/video', 'https://www.youtube.com/',
                                 'https://example.com/subs', 'https://example.com/audio'])
        args = extract.call_args.args[0]
        self.assertIn('--check-formats', args)
        self.assertNotIn('--no-check-formats', args)
        self.assertIn('bv*[height<=720]+ba/b[height<=720]', args[args.index('-f') + 1])
        self.assertEqual(args[args.index('-f') + 1], 'bv*[height<=720]+ba/b[height<=720]')

    def test_resolution_wins_over_protocol_with_real_format_selector(self):
        from yt_dlp import YoutubeDL
        formats = [dict(format_id=str(height), url='https://example.com/video.m3u8',
                        ext='mp4', height=height, width=height * 16 // 9,
                        vcodec='avc1', acodec='mp4a', protocol=protocol)
                   for height, protocol in [(144, 'm3u8_native'), (360, 'https'),
                                            (480, 'm3u8_native'), (720, 'm3u8_native'),
                                            (1080, 'm3u8_native')]]
        for quality, expected in [('1080p', 1080), ('720p', 720), ('480p', 480),
                                  ('best', 1080), ('worst', 144)]:
            with self.subTest(quality=quality), YoutubeDL(dict(
                    quiet=True, skip_download=True, check_formats=False,
                    format=media_sources.youtube_format(quality))) as extractor:
                result = extractor.process_ie_result(dict(
                    id='test', title='Test', formats=[dict(row) for row in formats]), download=False)
                self.assertEqual(result['height'], expected)

    def test_details_prepare_selected_stream_without_starting_player(self):
        import menu_requests
        engine = Mock()
        engine.history = {}
        engine.settings = {'mode': 'dub', 'quality': '720p'}
        show = {'id': 'youtube:test', 'kind': 'youtube', 'url': 'https://www.youtube.com/watch?v=test'}
        send = Mock()
        menu_requests.dispatch({'action': 'details', 'show': show}, engine, send)
        ready = engine.background.call_args.args[1]
        ready({'episodes': ['first', 'second'], 'resumeIndex': 1})
        send.assert_called_once()
        self.assertEqual(engine.resolve.call_args.args[0], ('youtube:test', 'second', 'dub', '720p'))
        engine.ensure_player.assert_not_called()
        engine.start_episode.assert_not_called()

    def test_feed_requires_explicit_connection(self):
        with patch.object(youtube_account, 'selection', return_value=''):
            with self.assertRaisesRegex(ValueError, 'Connect'):
                media_sources.youtube_for_you(1)

    def test_feed_pages_share_snapshot_and_refresh_replaces_it(self):
        cards = [{'id': str(i)} for i in range(45)]
        with patch.object(youtube_account, 'selection', return_value='firefox:profile'), \
             patch.object(youtube_account, 'assert_signed_in'), \
             patch.object(media_sources, 'fetch_youtube_feed', return_value=cards) as fetch, \
             patch.object(youtube_account, 'FEEDS', {}):
            self.assertEqual(len(media_sources.youtube_for_you(1)['items']), 20)
            self.assertEqual(media_sources.youtube_for_you(2)['items'], cards[20:40])
            self.assertFalse(media_sources.youtube_for_you(3)['hasMore'])
            self.assertEqual(fetch.call_count, 1)
            media_sources.youtube_for_you(1)
            self.assertEqual(fetch.call_count, 2)

    def test_queue_starts_at_selected_video_and_preserves_playlist(self):
        urls = ['https://www.youtube.com/watch?v=' + str(i) for i in range(3)]
        show = {'kind': 'youtube', 'title': 'Video', 'id': 'youtube:1'}
        cards = [{'url': url, 'title': str(i)} for i, url in enumerate(urls)]
        queued, episodes, index = media_sources.youtube_queue(show, [urls[1]], 0, cards)
        self.assertEqual((episodes, index), (urls, 1))
        self.assertEqual(queued['episodeLabels'][urls[2]], '2')
        self.assertEqual(media_sources.youtube_queue(show, urls, 0, list(reversed(cards))), (show, urls, 0))
        with self.assertRaises(ValueError):
            media_sources.youtube_queue(show, [urls[1]], 0, [{'url': 'https://example.com/secret'}])

    def test_connection_verified_before_saving_and_disconnect_removes_selection(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(youtube_account, 'CONFIG', Path(folder) / 'account.json'), \
             patch.object(youtube_account, 'browsers', return_value=[{'id':'firefox:profile','label':'Firefox'}]), \
             patch.object(youtube_account, 'assert_signed_in'):
            with self.assertRaises(ValueError):
                youtube_account.connect('firefox:profile', Mock(side_effect=ValueError('unavailable')))
            self.assertFalse(youtube_account.CONFIG.exists())
            self.assertTrue(youtube_account.connect('firefox:profile', Mock())['connected'])
            self.assertEqual(json.loads(youtube_account.CONFIG.read_text()), {'browser':'firefox:profile'})
            self.assertFalse(youtube_account.disconnect()['connected'])

    def test_youtube_auto_next_is_independent_and_never_advances_on_error(self):
        for enabled, reason, expected in [(True, 'eof', True), (False, 'eof', False), (True, 'error', False), (True, 'stop', False)]:
            engine = Mock()
            engine.play_token = 7
            show = {'id': 'youtube:1', 'kind': 'youtube', 'title': 'Video'}
            engine.context = (show, ['one', 'two'], 0, 7)
            engine.history = {}
            engine.settings = {'auto_next': False, 'youtube_auto_next': enabled}
            engine.episode_ended = engine.next_requested = False
            with patch.object(menu_backend, 'send'):
                menu_backend.Engine.player_event(engine, {'event':'end-file', 'reason':reason}, 7)
            self.assertEqual(engine.start_episode.called, expected)
            if expected:
                engine.start_episode.assert_called_once_with(show, ['one','two'], 1, 7, automatic=True)

    def test_account_option_only_used_after_connection(self):
        import subprocess
        with patch.object(youtube_account, 'selection', return_value='firefox:profile'), \
             patch.object(media_sources.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '{}', '')) as run:
            media_sources.ytdlp(['--', ':ytrec'])
            self.assertIn('--cookies-from-browser', run.call_args.args[0])
            self.assertIn('firefox:profile', run.call_args.args[0])
            media_sources.ytdlp(['--', ':ytrec'], browser='')
            self.assertNotIn('--cookies-from-browser', run.call_args.args[0])
