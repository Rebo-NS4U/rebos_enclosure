"""Check update states without changing Git refs or contacting GitHub."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('github_status', ROOT / 'payload/home/.config/quickshell/scripts/github_status.py')
status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(status)


class GithubStatusTests(unittest.TestCase):
    def check_result(self, comparison=None, dirty=False):
        replies = [{'default_branch': 'main'}, {'sha': 'remote' if comparison else 'local'}]
        if comparison:
            replies.append({'status': comparison, 'ahead_by': 3})
        with patch.object(status, 'installed', return_value=('local', dirty)), \
             patch.object(status, 'request', side_effect=replies):
            return status.check(Path('/unused'))

    def test_current_and_local_changes(self):
        self.assertEqual(self.check_result()['message'], 'Up to date')
        self.assertEqual(self.check_result(dirty=True)['message'], 'Up to date · local changes')

    def test_compare_direction(self):
        self.assertEqual(self.check_result('ahead')['status'], 'behind')
        self.assertIn('3 commits behind', self.check_result('ahead')['message'])
        self.assertEqual(self.check_result('behind')['status'], 'ahead')
        self.assertEqual(self.check_result('diverged')['status'], 'diverged')

    def test_unpublished_local_revision_compares_using_local_history(self):
        error = status.urllib.error.HTTPError('url', 404, 'Not found', {}, None)
        with patch.object(status, 'installed', return_value=('local', False)), \
             patch.object(status, 'request', side_effect=[{'default_branch': 'main'}, {'sha': 'remote'}, error]), \
             patch.object(status, 'linked_checkout', return_value=Path('/unused')), \
             patch.object(status, 'git', return_value='2 0'):
            result = status.check(Path('/tmp/checkout/desktop/payload/home'))
        self.assertEqual(result['status'], 'ahead')

    def test_missing_remote_revision_in_copied_installation(self):
        error = status.urllib.error.HTTPError('url', 404, 'Not found', {}, None)
        with patch.object(status, 'installed', return_value=('local', False)), \
             patch.object(status, 'request', side_effect=[{'default_branch': 'main'}, {'sha': 'remote'}, error]), \
             patch.object(status, 'linked_checkout', return_value=None):
            self.assertEqual(status.check(Path('/home/user'))['status'], 'unpublished')

    def test_network_failure_preserves_local_revision(self):
        with patch.object(status, 'installed', return_value=('local', True)), \
             patch.object(status, 'request', side_effect=OSError('offline')):
            result = status.check(Path('/unused'))
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['local'], 'local')
        self.assertIn('offline', result['message'])

    def test_copied_and_legacy_installation(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(status.os.environ, {}, clear=True):
            home = Path(temp)
            with self.assertRaisesRegex(ValueError, 'unknown'):
                status.installed(home)
            record = home / '.local/state/rebos-desktop/source.json'
            record.parent.mkdir(parents=True)
            record.write_text(json.dumps({'repository': status.REPOSITORY, 'commit': 'abc'}))
            self.assertEqual(status.installed(home), ('abc', False))

    def test_linked_installation_checks_origin_and_dirty_state(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            checkout = home / 'checkout'
            shell = checkout / 'desktop/payload/home/.config/quickshell'
            shell.mkdir(parents=True)
            (checkout / '.git').mkdir()
            (home / '.config').mkdir()
            (home / '.config/quickshell').symlink_to(shell)
            with patch.object(status, 'git', side_effect=[status.REPOSITORY + '.git', 'abc', ' M file']):
                self.assertEqual(status.installed(home), ('abc', True))
            with patch.object(status, 'git', return_value='https://example.com/other'):
                with self.assertRaisesRegex(ValueError, 'different'):
                    status.installed(home)


if __name__ == '__main__':
    unittest.main()
