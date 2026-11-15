"""Release-only availability and immediate, pinned updates."""
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch, Mock
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts'))
import github_update as updater


class UpdateTests(unittest.TestCase):
    def test_command_pins_release_and_skips_packages(self):
        with patch.object(updater, 'checkout', return_value=(Path('/repo'), 'Rebo-NS4U/rebos_enclosure')), patch.object(Path, 'is_file', return_value=True):
            self.assertEqual(updater.update_command('/repo', 'v2.0.0'),
                             ['bash', '/repo/update.sh', '--files-only', '--release', 'v2.0.0'])

    def test_regular_update_tracks_main_without_release_check(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0))
        with patch.object(updater, 'checkout', return_value=(Path('/repo'), 'Rebo-NS4U/rebos_enclosure')), patch.object(Path, 'is_file', return_value=True), patch.object(updater, 'release_status') as check:
            self.assertEqual(updater.perform('/repo', run=run), 0)
        run.assert_called_once_with(['bash', '/repo/update.sh', '--files-only', '--branch', 'main'])
        check.assert_not_called()

    def test_other_repository_is_rejected(self):
        with patch.object(updater, 'checkout', return_value=(Path('/repo'), 'other/repo')):
            with self.assertRaises(ValueError):
                updater.update_command('/repo', 'v2.0.0')

    def test_click_applies_once_without_confirmation(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0))
        with patch.object(updater, 'release_status', return_value=dict(available=True, tag='v2.0.0')), patch.object(updater, 'update_command', return_value=['updater', '--release', 'v2.0.0']):
            self.assertEqual(updater.perform('/repo', 'v2.0.0', run=run), 0)
        run.assert_called_once_with(['updater', '--release', 'v2.0.0'])

    def test_stale_button_never_applies(self):
        run = Mock()
        with patch.object(updater, 'release_status', return_value=dict(available=False)):
            with self.assertRaises(ValueError):
                updater.perform('/repo', 'v2.0.0', run=run)
        run.assert_not_called()

    def test_release_comparison_not_main_commits(self):
        for relation, expected in [('behind', True), ('current', False), ('ahead', False),
                                   ('diverged', False), ('unpublished', False)]:
            with self.subTest(relation=relation), patch.object(updater.status, 'installed', return_value=('installed', False)), patch.object(updater.status, 'request', side_effect=[dict(tag_name='v2.0.0'), dict(sha='released')]), patch.object(updater.status, 'compare_remote', side_effect=lambda fetch, result, *args: result.update(status=relation)):
                result = updater.release_status()
                self.assertEqual(result['available'], expected)
                self.assertEqual(result['tag'], 'v2.0.0')

    def test_no_release_is_not_an_update(self):
        error = urllib.error.HTTPError('test', 404, 'Not Found', {}, None)
        with patch.object(updater.status, 'installed', return_value=('installed', False)), patch.object(updater.status, 'request', side_effect=error):
            self.assertFalse(updater.release_status()['available'])

    def test_prereleases_and_drafts_are_not_updates(self):
        for release in [dict(prerelease=True), dict(draft=True)]:
            with patch.object(updater.status, 'installed', return_value=('installed', False)), patch.object(updater.status, 'request', return_value=release):
                self.assertFalse(updater.release_status()['available'])


if __name__ == '__main__':
    unittest.main()
