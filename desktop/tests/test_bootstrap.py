"""Exercise clone/update and argument forwarding against a real local Git repository."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / 'source'
        self.source.mkdir()
        self.clone = self.base / 'checkout'
        self.capture = self.base / 'arguments'
        self.env = dict(os.environ, REPO_URL=str(self.source), CLONE_DIR=str(self.clone),
                        BRANCH='main', CAPTURE=str(self.capture))
        self.git('init', '-b', 'main')
        (self.source / 'install.sh').write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$CAPTURE"\n')
        self.commit('Initial fixture')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.source), *args],
                              check=True, text=True, capture_output=True)

    def commit(self, message):
        self.git('add', '.')
        self.git('-c', 'user.name=Installer Test', '-c', 'user.email=installer@example.invalid',
                 'commit', '-m', message)

    def run_bootstrap(self):
        return subprocess.run(['bash', str(ROOT / 'oneline.sh'), '--dry-run', '--profile', 'core'],
                              env=self.env, input='', text=True, capture_output=True)

    def test_clone_and_fast_forward_keep_forwarded_arguments(self):
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.capture.read_text().splitlines(), ['--dry-run', '--profile', 'core'])
        (self.source / 'revision').write_text('updated')
        self.commit('Update fixture')
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.clone / 'revision').read_text(), 'updated')

    def test_dirty_checkout_is_preserved_and_not_executed(self):
        self.assertEqual(self.run_bootstrap().returncode, 0)
        self.capture.unlink()
        (self.clone / 'install.sh').write_text('local edits')
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('local edits', result.stderr)
        self.assertFalse(self.capture.exists())
        self.assertEqual((self.clone / 'install.sh').read_text(), 'local edits')

    def test_existing_non_repository_is_preserved(self):
        self.clone.mkdir()
        keep = self.clone / 'keep'
        keep.write_text('unrelated')
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Destination already exists', result.stderr)
        self.assertEqual(keep.read_text(), 'unrelated')


if __name__ == '__main__':
    unittest.main()
