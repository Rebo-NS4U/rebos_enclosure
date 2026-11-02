"""Run source desktop regressions against the portable media payload."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class MediaUpdateTests(unittest.TestCase):
    def test_media_regressions(self):
        root = Path(__file__).resolve().parents[1]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                   PYTHONPATH=str(root / 'payload/home/code/anime-streamer'))
        result = subprocess.run(
            [sys.executable, '-m', 'unittest', 'discover', '-s', str(root / 'tests/media'), '-q'],
            env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
