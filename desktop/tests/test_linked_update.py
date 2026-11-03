"""Preserved-source updates use temporary repositories, never the live desktop."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import linked_update
from linked_update import prepare, git
from deploy import verify


class PreservedUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'remote'
        self.remote.mkdir()
        git(self.remote, 'init', '-q', '-b', 'main')
        self.identify(self.remote)
        self.payload = self.remote / 'desktop/payload'
        source = self.payload / 'home/.config/quickshell'
        source.mkdir(parents=True)
        (source / 'shell.qml').write_text('old')
        (source / 'extra.qml').write_text('old extra')
        (self.payload / 'manifest.json').write_text(json.dumps({'units': ['.config/quickshell']}))
        for name in ('user.txt', 'staged.txt'):
            (self.remote / name).write_text('original\n')
        (self.remote / 'binary.dat').write_bytes(bytes(range(256)))
        self.seal(self.payload)
        self.commit(self.remote, 'Initial')
        self.local = self.root / 'local'
        subprocess.run(['git', 'clone', '-q', str(self.remote), str(self.local)], check=True)
        self.identify(self.local)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.initial = git(self.local, 'rev-parse', 'HEAD')

    def identify(self, root):
        git(root, 'config', 'user.name', 'Test')
        git(root, 'config', 'user.email', 'test@example.invalid')

    def seal(self, payload):
        hashes = {str(p.relative_to(payload)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(payload.rglob('*')) if p.is_file() and p.name != 'checksums.json'}
        (payload / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')

    def commit(self, root, message):
        git(root, 'add', '.')
        git(root, 'commit', '-qm', message)

    def incoming(self):
        (self.payload / 'home/.config/quickshell/shell.qml').write_text('new')
        self.seal(self.payload)
        self.commit(self.remote, 'Incoming')
        return git(self.remote, 'rev-parse', 'HEAD')

    def test_layout_transition_retains_local_code_edits_and_reviewed_untracked_source(self):
        extra = self.local / 'desktop/payload/home/.config/quickshell/local.qml'
        extra.write_text('local source')
        hashes_path = self.local / 'desktop/payload/checksums.json'
        hashes = json.loads(hashes_path.read_text())
        hashes['home/.config/quickshell/local.qml'] = hashlib.sha256(extra.read_bytes()).hexdigest()
        hashes_path.write_text(json.dumps(hashes))
        edited = self.local / 'desktop/payload/home/.config/quickshell/extra.qml'
        edited.write_text('my extra code')
        # The remote changes only organization, preserving code identity.
        new = self.remote / 'system/apps/shell'
        new.parent.mkdir(parents=True)
        git(self.remote, 'mv', 'desktop/payload/home/.config/quickshell', 'system/apps/shell')
        (self.remote / 'config').mkdir()
        data = {'layout': 2, 'units': ['.config/quickshell'], 'sources': {
            '.config/quickshell': {'source': 'system/apps/shell', 'kind': 'managed'}}}
        (self.payload / 'manifest.json').write_text(json.dumps(data))
        from layout import inventory
        new_hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in inventory(self.payload).items()}
        (self.payload / 'checksums.json').write_text(json.dumps(new_hashes))
        self.commit(self.remote, 'Separate system source')
        with prepare(self.local, self.remote, self.home) as staged:
            self.assertTrue(extra.exists(), 'Preview must retain the original live path')
            self.assertEqual((staged.plan / 'system/apps/shell/local.qml').read_text(), 'local source')
            staged.apply()
        self.assertFalse(extra.exists())
        self.assertEqual((self.local / 'system/apps/shell/local.qml').read_text(), 'local source')
        self.assertEqual((self.local / 'system/apps/shell/extra.qml').read_text(), 'my extra code')
        verify(self.local / 'desktop/payload')

    def test_dirty_preview_then_update_preserves_index_worktree_and_untracked(self):
        incoming = self.incoming()
        (self.local / 'user.txt').write_text('local edit\n')
        (self.local / 'staged.txt').write_text('staged edit\n')
        git(self.local, 'add', 'staged.txt')
        (self.local / 'notes.txt').write_text('untracked')
        before = git(self.local, 'status', '--porcelain')
        with prepare(self.local, self.remote, self.home) as staged:
            self.assertEqual(git(self.local, 'status', '--porcelain'), before)
            self.assertEqual(git(self.local, 'rev-parse', 'HEAD'), self.initial)
            staged.apply()
        self.assertEqual(git(self.local, 'rev-parse', 'HEAD'), incoming)
        self.assertEqual((self.local / 'user.txt').read_text(), 'local edit\n')
        self.assertEqual((self.local / 'notes.txt').read_text(), 'untracked')
        self.assertEqual(git(self.local, 'diff', '--cached', '--name-only'), 'staged.txt')
        self.assertEqual(git(self.local, 'diff', '--name-only'), 'user.txt')
        backup = next((self.home / '.local/state/rebos-desktop/local-source-backups').iterdir())
        self.assertEqual((backup / 'local-files.tar.gz').stat().st_mode & 0o777, 0o600)
        self.assertTrue((backup / 'stash.txt').exists())

    def test_conflicting_edits_leave_live_source_and_index_untouched(self):
        self.incoming()
        source = self.local / 'desktop/payload/home/.config/quickshell/shell.qml'
        source.write_text('local conflicting version')
        before = git(self.local, 'status', '--porcelain')
        with self.assertRaisesRegex(ValueError, 'Local edits conflict'):
            with prepare(self.local, self.remote, self.home):
                self.fail('A conflicted update must not be exposed to deployment')
        self.assertEqual(source.read_text(), 'local conflicting version')
        self.assertEqual(git(self.local, 'status', '--porcelain'), before)
        self.assertEqual(git(self.local, 'rev-parse', 'HEAD'), self.initial)

    def test_local_commits_are_merged_without_pushing(self):
        (self.local / 'local-commit.txt').write_text('keep commit')
        self.commit(self.local, 'Local commit')
        local_sha = git(self.local, 'rev-parse', 'HEAD')
        incoming = self.incoming()
        with prepare(self.local, self.remote, self.home) as staged:
            staged.apply()
        git(self.local, 'merge-base', '--is-ancestor', local_sha, 'HEAD')
        git(self.local, 'merge-base', '--is-ancestor', incoming, 'HEAD')
        self.assertEqual(git(self.remote, 'rev-parse', 'HEAD'), incoming)

    def test_untracked_collision_is_rejected_before_live_changes(self):
        (self.remote / 'collision.txt').write_text('remote')
        self.commit(self.remote, 'Collision')
        (self.local / 'collision.txt').write_text('mine')
        with self.assertRaisesRegex(ValueError, 'Untracked file conflicts'):
            with prepare(self.local, self.remote, self.home):
                self.fail('Untracked data must remain protected')
        self.assertEqual((self.local / 'collision.txt').read_text(), 'mine')
        self.assertEqual(git(self.local, 'rev-parse', 'HEAD'), self.initial)

    def test_generated_hashes_follow_preserved_sources(self):
        self.incoming()
        payload = self.local / 'desktop/payload'
        (payload / 'home/.config/quickshell/extra.qml').write_text('personal edit')
        self.seal(payload)
        with prepare(self.local, self.remote, self.home) as staged:
            verify(staged.plan / 'desktop/payload')
            staged.apply()
        verify(payload)
        self.assertEqual((payload / 'home/.config/quickshell/extra.qml').read_text(), 'personal edit')
        self.assertEqual((payload / 'home/.config/quickshell/shell.qml').read_text(), 'new')

    def test_already_current_source_refreshes_hashes_without_stashing_edits(self):
        payload = self.local / 'desktop/payload'
        source = payload / 'home/.config/quickshell/extra.qml'
        source.write_text('new personal edit')
        with prepare(self.local, self.remote, self.home) as staged:
            staged.apply()
        verify(payload)
        self.assertEqual(source.read_text(), 'new personal edit')
        self.assertEqual(git(self.local, 'rev-parse', 'HEAD'), self.initial)
        self.assertNotEqual(git(self.local, 'rev-parse', '--verify', 'refs/stash', check=False).returncode, 0)

    def test_binary_edits_are_preserved(self):
        self.incoming()
        contents = b'\x00\xfflocal binary\x00' * 20
        (self.local / 'binary.dat').write_bytes(contents)
        with prepare(self.local, self.remote, self.home) as staged:
            staged.apply()
        self.assertEqual((self.local / 'binary.dat').read_bytes(), contents)

    def test_editing_an_already_modified_file_cancels_apply(self):
        self.incoming()
        (self.local / 'user.txt').write_text('first edit')
        with prepare(self.local, self.remote, self.home) as staged:
            (self.local / 'user.txt').write_text('second edit')
            with self.assertRaisesRegex(ValueError, 'changed during'):
                staged.apply()
        self.assertEqual((self.local / 'user.txt').read_text(), 'second edit')

    def test_failed_merge_restores_edits_before_returning_error(self):
        self.incoming()
        (self.local / 'user.txt').write_text('keep my edit')
        real_git = linked_update.git
        def intercept(root, *args, **kwargs):
            if root == self.local and args[:1] == ('merge',):
                raise ValueError('simulated merge failure')
            return real_git(root, *args, **kwargs)
        with prepare(self.local, self.remote, self.home) as staged:
            with patch.object(linked_update, 'git', side_effect=intercept):
                with self.assertRaisesRegex(ValueError, 'recover local files'):
                    staged.apply()
        self.assertEqual((self.local / 'user.txt').read_text(), 'keep my edit')
        self.assertEqual(git(self.local, 'rev-parse', 'HEAD'), self.initial)

    def test_changed_live_source_cancels_apply(self):
        self.incoming()
        with prepare(self.local, self.remote, self.home) as staged:
            (self.local / 'user.txt').write_text('changed during preview')
            with self.assertRaisesRegex(ValueError, 'changed during'):
                staged.apply()
        self.assertEqual(git(self.local, 'rev-parse', 'HEAD'), self.initial)


if __name__ == '__main__':
    unittest.main()
