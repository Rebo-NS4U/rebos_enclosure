import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('develop', ROOT / 'desktop/scripts/develop.py')
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


class DevelopmentMenuTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.command('init', '-b', 'main')
        self.command('remote', 'add', 'origin', 'https://github.com/Rebo-NS4U/rebos_enclosure.git')
        self.command('config', 'user.name', 'Development Test')
        self.command('config', 'user.email', 'test@example.invalid')
        self.command('config', 'branch.main.remote', 'origin')
        self.command('config', 'branch.main.merge', 'refs/heads/main')
        (self.root / 'source.py').write_text('original\n')
        self.command('add', 'source.py')
        self.command('commit', '-m', 'initial')

    def command(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout

    def test_wrong_fetch_or_push_destination_is_refused(self):
        self.assertEqual(dev.verify_checkout(self.root), 'main')
        self.command('remote', 'set-url', '--push', 'origin', 'https://example.invalid/another.git')
        with self.assertRaisesRegex(ValueError, 'push destination'):
            dev.verify_checkout(self.root)
        self.command('remote', 'set-url', 'origin', 'https://example.invalid/another.git')
        with self.assertRaisesRegex(ValueError, 'official origin'):
            dev.verify_checkout(self.root)

    def test_stage_preserves_unrelated_edits_and_treats_paths_literally(self):
        (self.root / 'source.py').write_text('edited\n')
        (self.root / ':other file').write_text('new\n')
        dev.stage([':other file'], self.root)
        self.assertEqual(self.command('diff', '--cached', '--name-only').strip(), ':other file')
        self.assertIn('source.py', self.command('diff', '--name-only'))
        for paths in ([], ['.'], ['../outside'], ['source*'], [str(self.root / 'source.py')]):
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                dev.stage(paths, self.root)

    def test_push_is_one_explicit_branch_and_never_force(self):
        real = dev.run
        with patch.object(dev, 'run', wraps=dev.run) as runner:
            runner.side_effect = lambda args, root=dev.ROOT, capture=False: (
                subprocess.CompletedProcess(args, 0) if args[:2] == ['git', 'push'] else real(args, root, capture))
            dev.push(self.root)
            commands = [call.args[0] for call in runner.call_args_list]
            self.assertIn(['git', 'push', 'origin', 'HEAD:refs/heads/main'], commands)

    def test_outgoing_shows_only_commits_missing_from_push_destination(self):
        self.command('update-ref', 'refs/remotes/origin/main', 'HEAD')
        (self.root / 'source.py').write_text('new work\n')
        self.command('commit', '-am', 'Make the desktop easier to use')
        report = dev.outgoing(self.root)
        self.assertIn('origin/main: 1', report)
        self.assertIn('Make the desktop easier to use', report)
        self.assertNotIn('initial', report)
        self.assertIn('last fetched', report)
        self.command('update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.assertIn('No local commits waiting', dev.outgoing(self.root))

    def test_outgoing_handles_missing_remote_state_and_divergence(self):
        self.assertIn('unavailable', dev.outgoing(self.root))
        self.command('branch', 'remote-work')
        self.command('checkout', 'remote-work')
        (self.root / 'remote.txt').write_text('remote work')
        self.command('add', 'remote.txt')
        self.command('commit', '-m', 'Remote change')
        self.command('update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.command('checkout', 'main')
        report = dev.outgoing(self.root)
        self.assertIn('1 commits missing here', report)
        self.assertIn('No local commits waiting', report)

    def test_health_reports_service_access_failure_without_claiming_healthy(self):
        real_run = subprocess.run
        def run(command, **kwargs):
            if command[0] == 'systemctl':
                return subprocess.CompletedProcess(command, 1, '', 'No connection')
            return real_run(command, **kwargs)
        with patch.object(dev.subprocess, 'run', side_effect=run):
            report = dev.health_report(self.root)
        self.assertIn('Storage:', report)
        self.assertIn('Memory:', report)
        self.assertIn('could not check; service connection unavailable', report)
        self.assertNotIn('no failed services', report)
        self.assertIn('all changes are saved', report)
        (self.root / 'source.py').write_text('unsaved')
        with patch.object(dev.subprocess, 'run', side_effect=run):
            self.assertIn('not all been saved', dev.health_report(self.root))

    def test_pull_rejects_dirty_source_without_network(self):
        (self.root / 'source.py').write_text('local edits\n')
        with self.assertRaisesRegex(ValueError, 'local changes'):
            dev.action('pull', argparse.Namespace(), self.root)
        self.assertEqual((self.root / 'source.py').read_text(), 'local edits\n')

    def test_checksums_refuse_untracked_payload_before_writing(self):
        payload = self.root / 'desktop/payload'
        payload.mkdir(parents=True)
        (payload / 'manifest.json').write_text('{"units": []}\n')
        (payload / 'checksums.json').write_text('{}\n')
        self.command('add', 'desktop/payload/manifest.json', 'desktop/payload/checksums.json')
        (payload / 'secret.txt').write_text('not for shipping\n')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            dev.refresh_checksums(self.root)
        self.assertEqual(json.loads((payload / 'checksums.json').read_text()), {})

    def test_failed_index_verification_prevents_commit(self):
        (self.root / 'source.py').write_text('staged version\n')
        self.command('add', 'source.py')
        (self.root / 'source.py').write_text('unstaged version\n')
        head = self.command('rev-parse', 'HEAD')
        with self.assertRaises(subprocess.CalledProcessError):
            dev.commit('must not commit', self.root)
        self.assertEqual(self.command('rev-parse', 'HEAD'), head)
        self.assertEqual((self.root / 'source.py').read_text(), 'unstaged version\n')
        self.assertEqual(self.command('show', ':source.py'), 'staged version\n')

    def test_commit_checks_the_index_and_preserves_unstaged_edits(self):
        scripts = self.root / 'desktop/scripts'
        scripts.mkdir(parents=True)
        (scripts / 'deploy.py').write_text(
            'from pathlib import Path\nassert Path("source.py").read_text() == "staged version\\n"\n')
        tests = self.root / 'desktop/tests'
        tests.mkdir()
        (tests / 'test_export.py').write_text(
            'import unittest\nfrom pathlib import Path\n'
            'class ExportTest(unittest.TestCase):\n'
            '    def test_staged_source(self):\n'
            '        self.assertEqual(Path("source.py").read_text(), "staged version\\n")\n')
        (self.root / 'source.py').write_text('staged version\n')
        self.command('add', 'source.py', 'desktop/scripts/deploy.py', 'desktop/tests/test_export.py')
        (self.root / 'source.py').write_text('unstaged version\n')
        dev.commit('verified index', self.root)
        self.assertEqual(self.command('show', 'HEAD:source.py'), 'staged version\n')
        self.assertEqual((self.root / 'source.py').read_text(), 'unstaged version\n')
        self.assertIn('source.py', self.command('diff', '--name-only'))



if __name__ == '__main__':
    unittest.main()
