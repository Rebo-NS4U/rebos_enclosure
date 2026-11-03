"""Verify the Settings update action never applies after a failed or cancelled preview."""
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'payload/home/.config/quickshell/scripts'))
import github_update as updater


class UpdateTests(unittest.TestCase):
    def test_command_defaults_to_files_only(self):
        with patch.object(updater, 'checkout', return_value=(Path('/repo'), 'Rebo-NS4U/rebos_enclosure')), patch.object(Path, 'is_file', return_value=True):
            self.assertEqual(updater.update_command('/repo'), ['bash', '/repo/update.sh', '--files-only'])
            self.assertNotIn('--files-only', updater.update_command('/repo', True))

    def test_other_repository_is_rejected(self):
        with patch.object(updater, 'checkout', return_value=(Path('/repo'), 'other/repo')):
            with self.assertRaises(ValueError):
                updater.update_command('/repo')

    def test_missing_updater_is_rejected(self):
        with patch.object(updater, 'checkout', return_value=(Path('/repo'), 'Rebo-NS4U/rebos_enclosure')), patch.object(Path, 'is_file', return_value=False):
            with self.assertRaises(ValueError):
                updater.update_command('/repo')

    def test_failed_preview_never_applies(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 1))
        ask = Mock()
        with patch.object(updater, 'update_command', return_value=['updater']):
            self.assertEqual(updater.perform('/repo', run=run, ask=ask), 1)
        run.assert_called_once_with(['updater', '--dry-run'])
        ask.assert_not_called()

    def test_cancel_never_applies(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0))
        with patch.object(updater, 'update_command', return_value=['updater']):
            self.assertEqual(updater.perform('/repo', run=run, ask=lambda _: ''), 0)
        run.assert_called_once()

    def test_confirmation_applies_and_reports_failure(self):
        run = Mock(side_effect=[subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 2)])
        with patch.object(updater, 'update_command', return_value=['updater', '--files-only']):
            self.assertEqual(updater.perform('/repo', run=run, ask=lambda _: 'UPDATE'), 2)
        self.assertEqual(run.call_args_list[1].args[0], ['updater', '--files-only'])

if __name__ == '__main__':
    unittest.main()
