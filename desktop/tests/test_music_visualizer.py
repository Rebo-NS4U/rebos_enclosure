"""Verify spectrum response and that the output monitor is cleaned up on exit."""
import importlib.util
import io
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

    def test_output_monitor_and_cleanup(self):
        child = Mock(stdout=io.BytesIO(b''))
        with patch.object(visualizer.subprocess, 'Popen', return_value=child) as start, \
             patch.object(visualizer.signal, 'signal'):
            visualizer.main()
        self.assertIn('--device=@DEFAULT_MONITOR@', start.call_args.args[0])
        child.terminate.assert_called_once()
        child.wait.assert_called_once_with(timeout=2)


if __name__ == '__main__':
    unittest.main()
