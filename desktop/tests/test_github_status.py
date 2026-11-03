"""Check update states without changing Git refs or contacting GitHub."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('github_status', ROOT.parent / 'system/apps/shell/scripts/github_status.py')
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

    def test_changed_files_preserves_paths_and_skips_rename_source(self):
        raw = ' M space name.qml\0R  new name.qml\0old name.qml\0?? extra/\0UD conflict.qml\0'
        self.assertEqual(status.changed_files(raw), [
            {'path': 'space name.qml', 'kind': 'Modified'},
            {'path': 'new name.qml', 'kind': 'Renamed'},
            {'path': 'extra/', 'kind': 'Untracked'},
            {'path': 'conflict.qml', 'kind': 'Conflicted'}])

    def test_remote_metadata_and_comparison_counts(self):
        commit = {'sha': 'remote', 'commit': {'message': 'New version\n\nDetails',
                  'author': {'name': 'Maintainer', 'date': '2026-11-02T12:00:00Z'}}}
        with patch.object(status, 'installed', return_value=('local', False)), \
             patch.object(status, 'request', side_effect=[{'default_branch': 'main'}, commit,
                 {'status': 'ahead', 'ahead_by': 3, 'behind_by': 0, 'commits': [commit]}]):
            result = status.check(Path('/unused'))
        self.assertEqual(result['remote_commit']['title'], 'New version')
        self.assertEqual(result['remote_commit']['author'], 'Maintainer')
        self.assertEqual(result['default_branch'], 'main')
        self.assertEqual((result['ahead'], result['behind']), (0, 3))
        self.assertEqual(result['incoming'][0]['sha'], 'remote')
        self.assertTrue(result['checked_at'])

    def test_large_comparison_uses_last_page_for_recent_commits(self):
        newest = {'sha': 'newest', 'commit': {'message': 'Newest change'}}
        with patch.object(status, 'installed', return_value=('local', False)), \
             patch.object(status, 'request', side_effect=[{'default_branch': 'main'}, {'sha': 'remote'},
                 {'status': 'ahead', 'ahead_by': 300, 'behind_by': 0, 'total_commits': 300},
                 {'commits': [newest]}]) as request:
            result = status.check(Path('/unused'))
        self.assertEqual(result['incoming'][0]['sha'], 'newest')
        self.assertTrue(request.call_args.args[0].endswith('?per_page=5&page=60'))
        self.assertEqual(result['behind'], 300)

    def test_local_metadata_and_change_list_limit(self):
        result = {}
        with patch.object(status, 'linked_checkout', return_value=Path('/unused')), \
             patch.object(status, 'git', side_effect=['HEAD', 'Title' + '\0' + 'Author' + '\0' + '2026-11-02',
                 ''.join(' M file' + str(i) + '\0' for i in range(15))]):
            status.local_details(Path('/unused'), result)
        self.assertEqual(result['branch'], 'Detached HEAD')
        self.assertEqual(result['installation'], 'Linked source checkout')
        self.assertEqual(result['local_commit']['title'], 'Title')
        self.assertEqual(result['local_commit']['author'], 'Author')
        self.assertEqual(result['change_count'], 15)
        self.assertEqual(len(result['changes']), 12)

    def test_optional_local_metadata_failure_does_not_hide_sync(self):
        with patch.object(status, 'local_details', side_effect=OSError('details unavailable')):
            result = self.check_result()
        self.assertEqual(result['status'], 'current')
        self.assertIn('details unavailable', result['details_error'])

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
        self.addCleanup(error.close)
        with patch.object(status, 'installed', return_value=('local', False)), \
             patch.object(status, 'request', side_effect=[{'default_branch': 'main'}, {'sha': 'remote'}, error]), \
             patch.object(status, 'linked_checkout', return_value=Path('/unused')), \
             patch.object(status, 'git', return_value='2 0'):
            result = status.check(Path('/tmp/checkout/desktop/payload/home'))
        self.assertEqual(result['status'], 'ahead')

    def test_missing_remote_revision_in_copied_installation(self):
        error = status.urllib.error.HTTPError('url', 404, 'Not found', {}, None)
        self.addCleanup(error.close)
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
