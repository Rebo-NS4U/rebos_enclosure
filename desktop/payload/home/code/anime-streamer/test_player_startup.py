import subprocess
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, Mock
import vlc_session
from primewire_source import PlaybackLinks


class NetworkPlaybackTests(unittest.TestCase):
    def test_mp4_uses_ffmpeg_demuxer_without_forcing_hls_or_matroska(self):
        for format_name in ('mov,mp4,m4a,3gp,3g2,mj2', 'hls', 'matroska,webm', ''):
            with self.subTest(format_name=format_name), tempfile.TemporaryDirectory() as folder:
                session = vlc_session.VlcSession.__new__(vlc_session.VlcSession)
                session.audio_normalization = False
                session.generation = 0
                session.logpath = Path(folder) / 'vlc.log'
                session.logpath.touch()
                session.api = Mock()
                session.public_stream = lambda url, referer: url
                links = PlaybackLinks('http://127.0.0.1:1234/media/1', 0)
                links.format_name = format_name
                session.apply(['load', links, 'Network clip', False, True])
                options = json.loads(session.api.call_args.kwargs['data'])['options']
                self.assertIn('network-caching=5000', options)
                self.assertIn('prefetch-buffer-size=65536', options)
                self.assertEqual('demux=avformat' in options, format_name.startswith('mov,'))


class PluginDetectionTests(unittest.TestCase):
    def test_available_options(self):
        with patch.object(vlc_session.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '--pause-click-mouse-button')):
            self.assertTrue(vlc_session.pause_click_available())

    def test_missing_plugin(self):
        with patch.object(vlc_session.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'No matching module found')):
            self.assertFalse(vlc_session.pause_click_available())

    def test_failed_probe(self):
        for error in (OSError('missing executable'), subprocess.TimeoutExpired('vlc', 5)):
            with self.subTest(error=error), patch.object(vlc_session.subprocess, 'run', side_effect=error):
                self.assertFalse(vlc_session.pause_click_available())


if __name__ == '__main__':
    unittest.main()
