"""Process labels distinguish workers without exposing full command lines."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/process_monitor.py'
spec = importlib.util.spec_from_file_location('process_monitor', SOURCE)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class ProcessNameTests(unittest.TestCase):
    def test_specific_names_and_private_arguments(self):
        cases = [('/usr/bin/python3.14', b'python3\0/home/user/process_monitor.py\0--token=secret\0', 'process_monitor.py (python3.14)'),
                 ('/usr/bin/python3', b'python3\0-m\0http.server\0', 'http.server (python3)'),
                 ('/opt/browser/chromium', b'chromium\0--type=renderer\0https://private\0', 'chromium · Renderer'),
                 ('/opt/app/long-executable-name', b'app\0secret\0', 'long-executable-name'),
                 ('/usr/bin/bash', b'bash\0-c\0secret command\0', 'bash')]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for exe, argv, expected in cases:
                with self.subTest(exe=exe):
                    (base / 'cmdline').write_bytes(argv)
                    with patch.object(monitor.os, 'readlink', return_value=exe):
                        self.assertEqual(monitor.process_name(base, 'fallback'), expected)

    def test_unavailable_process_falls_back(self):
        with patch.object(monitor.os, 'readlink', side_effect=PermissionError):
            self.assertEqual(monitor.process_name(Path('/missing'), 'kernel worker'), 'kernel worker')
        with patch.object(monitor.os, 'readlink', return_value='/usr/bin/example'):
            self.assertEqual(monitor.process_name(Path('/missing'), 'fallback'), 'example')
