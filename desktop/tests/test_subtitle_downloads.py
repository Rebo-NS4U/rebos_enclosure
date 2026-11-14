"""Verify subtitle assets before replacing an existing installation."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('subtitle_setup', ROOT / 'desktop/scripts/setup-subtitles.py')
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class SubtitleDownloadTests(unittest.TestCase):
    def test_valid_cache_is_reused_and_corruption_is_replaced(self):
        data = b'verified asset'
        digest = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.bin'
            path.write_bytes(data)
            with patch.object(setup.urllib.request, 'urlopen') as fetch:
                setup.download('https://example.com/model', path, digest)
                fetch.assert_not_called()
            path.write_bytes(b'corrupt cache')
            with patch.object(setup.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
                setup.download('https://example.com/model', path, digest)
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_mismatch_and_network_failure_preserve_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.bin'
            path.write_bytes(b'previous model')
            for failure in (False, True):
                with self.subTest(network_failure=failure):
                    options = {'side_effect': OSError('offline')} if failure else {'return_value': io.BytesIO(b'wrong asset')}
                    with patch.object(setup.urllib.request, 'urlopen', **options):
                        with self.assertRaises((OSError, RuntimeError)):
                            setup.download('https://example.com/model', path, '0' * 64)
                    self.assertEqual(path.read_bytes(), b'previous model')
                    self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_moviebox_provenance_files_are_shipped(self):
        vendor = ROOT / 'system/apps/media/vendor/moviebox-tui'
        self.assertIn('MovieBox-Tui', (vendor / 'SOURCE.md').read_text())
        self.assertIn('MIT License', (vendor / 'LICENSE-MIT').read_text())
