import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from publish import publish, validate, git


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'checkout'
        self.remote = self.root / 'remote.git'
        self.home = self.root / 'source-home'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.repo)], check=True)
        subprocess.run(['git', 'init', '-q', '--bare', str(self.remote)], check=True)
        git(self.repo, 'config', 'user.name', 'Publisher test')
        git(self.repo, 'config', 'user.email', 'publisher@example.invalid')
        self.content = 'first'
        self.build(self.home, self.repo / 'desktop/payload')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-m', 'Initial fixture')
        git(self.repo, 'remote', 'add', 'origin', str(self.remote))
        git(self.repo, 'push', '-u', 'origin', 'main')
        self.before = git(self.repo, 'rev-parse', 'HEAD')

    def build(self, home, output):
        config = output / 'home/.config/example.conf'
        config.parent.mkdir(parents=True)
        config.write_text(self.content)
        (output / 'manifest.json').write_text(json.dumps({'created': self.content, 'units': ['.config/example.conf']}))
        hashes = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in output.rglob('*') if p.is_file()}
        (output / 'checksums.json').write_text(json.dumps(hashes))

    def test_dry_run_then_real_publish_and_repeat_without_commit(self):
        self.content = 'second'
        publish(self.repo, self.home, dry_run=True, builder=self.build)
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), self.before)
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')
        publish(self.repo, self.home, builder=self.build)
        self.assertEqual(git(self.remote, 'show', 'main:desktop/payload/home/.config/example.conf'), 'second')
        head = git(self.repo, 'rev-parse', 'HEAD')
        self.assertNotEqual(head, self.before)
        publish(self.repo, self.home, builder=self.build)
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), head)
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')

    def test_dirty_checkout_is_preserved(self):
        file = self.repo / 'desktop/payload/home/.config/example.conf'
        file.write_text('user edits')
        with self.assertRaisesRegex(ValueError, 'uncommitted'):
            publish(self.repo, self.home, builder=self.build)
        self.assertEqual(file.read_text(), 'user edits')
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), self.before)

    def test_divergent_remote_is_not_overwritten(self):
        peer = self.root / 'peer'
        subprocess.run(['git', 'clone', '-q', '-b', 'main', str(self.remote), str(peer)], check=True)
        git(peer, 'config', 'user.name', 'Other editor')
        git(peer, 'config', 'user.email', 'other@example.invalid')
        (peer / 'README.md').write_text('remote work')
        git(peer, 'add', '.')
        git(peer, 'commit', '-m', 'Remote work')
        git(peer, 'push', 'origin', 'main')
        remote_head = git(peer, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(ValueError, 'branches differ'):
            publish(self.repo, self.home, builder=self.build)
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), remote_head)
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), self.before)

    def test_snapshot_failure_preserves_existing_payload(self):
        def broken(home, output):
            raise OSError('Source missing')
        with self.assertRaises(OSError):
            publish(self.repo, self.home, builder=broken)
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), self.before)

    def test_private_state_and_checksum_failure_are_rejected(self):
        fresh = self.root / 'payload'
        self.build(self.home, fresh)
        target = fresh / 'home/.config/example.conf'
        target.write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'checksums'):
            validate(fresh, self.home)
        key = fresh / 'home/.ssh/id_test'
        key.parent.mkdir()
        key.write_text('private')
        hashes = {str(p.relative_to(fresh)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in fresh.rglob('*') if p.is_file() and p.name != 'checksums.json'}
        (fresh / 'checksums.json').write_text(json.dumps(hashes))
        with self.assertRaisesRegex(ValueError, 'Private state'):
            validate(fresh, self.home)


if __name__ == '__main__':
    unittest.main()
