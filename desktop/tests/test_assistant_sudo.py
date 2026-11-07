"""Check approval and credential reuse without invoking sudo or password dialogs."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/assistant_sudo.py'
spec = importlib.util.spec_from_file_location('assistant_sudo', SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class AdministratorApprovalTests(unittest.TestCase):
    def invoke(self, approval_status):
        with patch.dict(os.environ, {'WAYLAND_DISPLAY': 'test-display'}), \
             patch('sys.argv', ['assistant-sudo', '--reason', 'Test operation', '--', 'true']), \
             patch.object(helper.subprocess, 'run', side_effect=[
                 SimpleNamespace(returncode=approval_status), SimpleNamespace(returncode=0)
             ]) as run:
            status = helper.main()
        return status, run.call_args_list

    def test_cached_authentication_still_requires_command_approval(self):
        status, calls = self.invoke(0)
        self.assertEqual(status, 0)
        self.assertIn('approve', calls[0].args[0])
        self.assertEqual(calls[1].args[0], ['/usr/bin/sudo', '-A', '--', 'true'])
        self.assertTrue(calls[1].kwargs['env']['SUDO_ASKPASS'].endswith('assistant_sudo_askpass.sh'))

    def test_cancel_never_invokes_sudo(self):
        status, calls = self.invoke(1)
        self.assertEqual(status, 1)
        self.assertEqual(len(calls), 1)
