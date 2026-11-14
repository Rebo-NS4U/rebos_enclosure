import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/screen_text.py'
spec = importlib.util.spec_from_file_location('screen_text', SCRIPT)
ocr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ocr)


class ScreenTextTest(unittest.TestCase):
    def test_cancel_does_not_capture_or_copy(self):
        with patch.object(ocr.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)) as run:
            self.assertEqual(ocr.capture(), {'cancelled': True})
            self.assertEqual(run.call_count, 1)

    def test_capture_cleanup_and_plain_text(self):
        captures = []
        def run(args, **kwargs):
            if args[0] == 'slurp':
                return subprocess.CompletedProcess(args, 0, '10,20 400x120\n')
            if args[0] == 'grim':
                captures.append(Path(args[-1]))
                captures[-1].write_bytes(b'image')
                self.assertEqual(args[2], '10,20 400x120')
                return subprocess.CompletedProcess(args, 0)
            self.assertTrue(captures[0].exists())
            return subprocess.CompletedProcess(args, 0, '  Text & symbols <script>\n')
        with patch.object(ocr.subprocess, 'run', side_effect=run):
            self.assertEqual(ocr.capture()['text'], 'Text & symbols <script>')
        self.assertFalse(captures[0].exists())

    def test_empty_result_has_useful_error(self):
        with patch.object(ocr.subprocess, 'run', side_effect=[
            subprocess.CompletedProcess([], 0, '0,0 10x10'),
            subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 0, '\n')]):
            self.assertIn('No text found', ocr.capture()['error'])

    def test_capture_failure_cleans_temp_directory(self):
        paths = []
        def run(args, **kwargs):
            if args[0] == 'slurp':
                return subprocess.CompletedProcess(args, 0, '0,0 10x10')
            paths.append(Path(args[-1]).parent)
            raise subprocess.CalledProcessError(1, args)
        with patch.object(ocr.subprocess, 'run', side_effect=run):
            with self.assertRaises(subprocess.CalledProcessError):
                ocr.capture()
        self.assertFalse(paths[0].exists())
