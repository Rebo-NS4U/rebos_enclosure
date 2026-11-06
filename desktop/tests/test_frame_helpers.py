"""Frame renderers share result handling without running video processes."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FrameHelperTests(unittest.TestCase):
    def test_success_requires_an_output_file(self):
        helper = load('frame_helpers')
        with patch.object(helper.subprocess, 'run', return_value=Mock(returncode=0, stderr='')) as run:
            output = Mock()
            output.exists.return_value = True
            self.assertEqual(helper.render_frame(['fake'], output), (True, 'Success'))
            self.assertEqual(run.call_args.kwargs['timeout'], 30)
            output.exists.return_value = False
            self.assertEqual(helper.render_frame(['fake'], output), (False, 'Unknown error'))

    def test_timeout_and_error_messages_are_preserved(self):
        helper = load('frame_helpers')
        with patch.object(helper.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fake', 30)):
            self.assertEqual(helper.render_frame(['fake'], Mock()), (False, 'Timeout'))
        with patch.object(helper.subprocess, 'run', return_value=Mock(returncode=1, stderr=' failed\n')):
            self.assertEqual(helper.render_frame(['fake'], Mock()), (False, 'failed'))

    def test_console_close_preserves_exit_code(self):
        helper = load('console_helpers')
        for error in (EOFError, KeyboardInterrupt):
            with patch('builtins.input', side_effect=error):
                self.assertEqual(helper.close_console(7), 7)
