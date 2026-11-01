"""Check source freshness with real local Git repositories; never install files."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class InstallSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rebos-source-test-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / 'remote'
        self.checkout = self.base / 'old-checkout'
        self.source.mkdir()
        (self.source / 'desktop').mkdir()
        shutil.copyfile(ROOT / 'install.sh', self.source / 'install.sh')
        (self.source / 'desktop/install.sh').write_text('''#!/usr/bin/env bash
set -eu
directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cat "$directory/revision" > "$CAPTURE.revision"
printf '%s\\n' "$directory" > "$CAPTURE.directory"
printf '%s\\n' "$@" > "$CAPTURE.args"
exit "${INSTALL_EXIT_CODE:-0}"
''')
        (self.source / 'desktop/revision').write_text('old')
        self.git('init', '-b', 'main')
        self.commit('Old source')
        subprocess.run(['git', 'clone', str(self.source), str(self.checkout)],
                       check=True, capture_output=True)
        (self.source / 'desktop/revision').write_text('new-regreet')
        self.commit('New source with ReGreet')
        self.capture = self.base / 'capture'
        self.env = dict(os.environ, REPO_URL=str(self.source), CAPTURE=str(self.capture))
        self.env.pop('BRANCH', None)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.source), *args],
                              check=True, capture_output=True, text=True)

    def commit(self, message):
        self.git('add', '.')
        self.git('-c', 'user.name=Installer Test', '-c', 'user.email=test@example.invalid',
                 'commit', '-m', message)

    def run_installer(self, *args, desktop=False):
        script = self.checkout / ('desktop/install.sh' if desktop else 'install.sh')
        return subprocess.run(['bash', str(script), *args], env=self.env,
                              capture_output=True, text=True, timeout=20)

    def captured(self, suffix):
        return Path(str(self.capture) + '.' + suffix)

    def test_stale_dirty_checkout_installs_new_source_and_forwards_arguments(self):
        (self.checkout / 'desktop/revision').write_text('personal edit')
        args = ['--dry-run', '--profile', 'core', '--monitors', 'relative monitor file.json']
        result = self.run_installer(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.captured('revision').read_text(), 'new-regreet')
        self.assertEqual(self.captured('args').read_text().splitlines(), args)
        self.assertEqual((self.checkout / 'desktop/revision').read_text(), 'personal edit')
        self.assertIn(self.git('rev-parse', 'HEAD').stdout.strip(), result.stdout)
        self.assertFalse(Path(self.captured('directory').read_text().strip()).exists())

    def test_fetch_failure_never_runs_old_installer(self):
        self.env['REPO_URL'] = str(self.base / 'missing-remote')
        result = self.run_installer('--dry-run')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('No local fallback', result.stderr)
        self.assertFalse(self.captured('revision').exists())

    def test_explicit_local_snapshot_works_offline(self):
        self.env['REPO_URL'] = str(self.base / 'missing-remote')
        result = self.run_installer('--local-snapshot', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.captured('revision').read_text(), 'old')

    def test_help_works_offline(self):
        self.env['REPO_URL'] = str(self.base / 'missing-remote')
        result = self.run_installer('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('Fetching', result.stdout)

    def test_direct_desktop_entry_also_fetches(self):
        shutil.copyfile(ROOT / 'desktop/install.sh', self.checkout / 'desktop/install.sh')
        result = self.run_installer('--dry-run', desktop=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.captured('revision').read_text(), 'new-regreet')

    def test_failed_install_propagates_status_and_cleans_snapshot(self):
        self.env['INSTALL_EXIT_CODE'] = '19'
        result = self.run_installer('--dry-run')
        self.assertEqual(result.returncode, 19, result.stderr)
        self.assertFalse(Path(self.captured('directory').read_text().strip()).exists())

    def test_explicit_branch_is_used(self):
        self.git('branch', 'alternate', 'HEAD~1')
        self.env['BRANCH'] = 'alternate'
        result = self.run_installer('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.captured('revision').read_text(), 'old')

    def test_release_selects_exact_tag_and_strips_selector(self):
        self.git('-c', 'user.name=Installer Test', '-c', 'user.email=test@example.invalid',
                 'tag', '-a', 'v1.3.0', 'HEAD~1', '-m', 'Release')
        # A branch with the same name must not override the release tag.
        self.git('branch', 'v1.3.0')
        for selector in (['--release', 'v1.3.0'], ['--release=v1.3.0']):
            with self.subTest(selector=selector):
                result = self.run_installer(*selector, '--dry-run', '--profile', 'core')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.captured('revision').read_text(), 'old')
                self.assertEqual(self.captured('args').read_text().splitlines(),
                                 ['--dry-run', '--profile', 'core'])
                self.assertFalse(Path(self.captured('directory').read_text().strip()).exists())

    def test_direct_desktop_release_selection(self):
        self.git('tag', 'v1.3.0', 'HEAD~1')
        shutil.copyfile(ROOT / 'desktop/install.sh', self.checkout / 'desktop/install.sh')
        result = self.run_installer('--release', 'v1.3.0', '--dry-run', desktop=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.captured('revision').read_text(), 'old')

    def test_missing_release_does_not_fall_back_to_branch(self):
        self.git('branch', 'v9.9.9')
        result = self.run_installer('--release', 'v9.9.9', '--dry-run')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('No local fallback', result.stderr)
        self.assertFalse(self.captured('revision').exists())

    def test_invalid_and_conflicting_release_options(self):
        for args in (['--release'], ['--release='], ['--release', '../bad'],
                     ['--release', 'v1.3.0', '--local-snapshot']):
            with self.subTest(args=args):
                result = self.run_installer(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.captured('revision').exists())
        self.env['BRANCH'] = 'main'
        result = self.run_installer('--release', 'v1.3.0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('cannot be combined', result.stderr)


if __name__ == '__main__':
    unittest.main()
