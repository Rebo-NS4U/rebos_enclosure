"""Verify spectrum response and that the output monitor is cleaned up on exit."""
import importlib.util
import math
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/music_visualizer.py'
spec = importlib.util.spec_from_file_location('music_visualizer', SOURCE)
visualizer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visualizer)


class MusicVisualizerTests(unittest.TestCase):
    def test_silence(self):
        self.assertEqual(visualizer.spectrum([0] * visualizer.SIZE), [0] * visualizer.BANDS)

    def test_frequency_and_loudness(self):
        def tone(frequency, volume):
            return visualizer.spectrum([int(volume * math.sin(2 * math.pi * frequency * n / visualizer.RATE))
                                        for n in range(visualizer.SIZE)])
        bass, treble = tone(120, 10000), tone(4000, 10000)
        self.assertLess(bass.index(max(bass)), treble.index(max(treble)))
        self.assertLess(max(tone(120, 500)), max(bass))
        self.assertTrue(all(0 <= value <= 1 for value in bass + treble))

    def test_regular_audio_without_mpris_and_system_exclusion(self):
        def stream(index, **props):
            return dict(index=index, sink=7, corked=False, mute=False, properties=props)
        streams = [stream(1), stream(2, **{'media.role': 'event'}),
                   stream(3, **{'application.id': 'org.quickshell'}),
                   stream(4, **{'media.role': 'music'}),
                   dict(stream(5), corked=True), dict(stream(6), mute=True),
                   stream(7, **{'application.id': 'org.quickshell',
                                'media.name': 'QtmPulseStream-123-456'}),
                   stream(8, **{'application.id': 'org.quickshell',
                                'media.name': 'QtmPulseStream-123-789',
                                'media.role': 'event'}),
                   stream(9, **{'application.process.binary': 'qs'})]
        import json
        with patch.object(visualizer.subprocess, 'run', side_effect=[
            Mock(stdout=json.dumps(streams)),
            Mock(stdout=json.dumps([dict(index=7, monitor_source='output.monitor')]))]):
            self.assertEqual(visualizer.playback_streams(),
                             {1: 'output.monitor', 4: 'output.monitor', 7: 'output.monitor'})

    def test_cleanup_on_exit(self):
        child = Mock()
        with patch.object(visualizer, 'playback_streams', return_value={1: 'output.monitor'}), \
             patch.object(visualizer.subprocess, 'Popen', return_value=child) as start, \
             patch.object(visualizer.signal, 'signal'), \
             patch.object(visualizer.os, 'set_blocking'), \
             patch.object(visualizer.selectors, 'DefaultSelector') as selector:
            selector.return_value.__enter__.return_value = selector.return_value
            selector.return_value.select.side_effect = BrokenPipeError
            visualizer.main()
        self.assertIn('--device=output.monitor', start.call_args.args[0])
        self.assertIn('--monitor-stream=1', start.call_args.args[0])
        child.terminate.assert_called_once()
