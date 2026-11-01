"""Exercise remote fetching and preference preservation without touching the desktop."""
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
import update

SCRIPT = Path(__file__).resolve().parents[2] / 'update.sh'


class PackageApprovalTests(unittest.TestCase):
    def test_package_upgrade_approval_command(self):
        for helper_exists in (True, False):
            with self.subTest(helper_exists=helper_exists), tempfile.TemporaryDirectory() as temporary:
                home = Path(temporary)
                helper = home / '.local/bin/assistant-sudo'
                if helper_exists:
                    helper.parent.mkdir(parents=True)
                    helper.touch()
                with patch.object(sys, 'argv', ['update.py', '--no-aur']), \
                     patch.dict(os.environ, {key: str(home / relative) for key, relative in [
                         ('XDG_CONFIG_HOME', '.config'), ('XDG_CACHE_HOME', '.cache'),
                         ('XDG_DATA_HOME', '.local/share'), ('XDG_STATE_HOME', '.local/state')]}), \
                     patch.object(update.Path, 'home', return_value=home), \
                     patch.object(update.os, 'geteuid', return_value=1000), \
                     patch.object(update.Path, 'exists', return_value=True), \
                     patch.object(update, 'run') as run, \
                     patch.object(update.subprocess, 'check_output', return_value='test-commit'), \
                     patch.object(update, 'apply_snapshot'):
                    update.main()
                expected = (str(helper), '--reason',
                            'Upgrade installed system packages before updating the desktop',
                            '--', 'pacman', '-Syu') if helper_exists else ('sudo', 'pacman', '-Syu')
                self.assertEqual(run.call_args_list[1].args, expected)


@unittest.skipIf(os.geteuid() == 0, 'Updater intentionally refuses root')
class UpdateTests(unittest.TestCase):
    def test_fetch_preview_apply_and_repeat(self):
        self.exercise_update()

    def test_release_preview_apply_and_repeat(self):
        self.exercise_update('v1.3.0')

    def test_missing_release_does_not_fall_back_to_branch(self):
        self.exercise_update('v9.9.9')

    def test_invalid_and_conflicting_release_options(self):
        for options in (['--release'], ['--release='], ['--release', '../bad'],
                        ['--release', 'v1.3.0', '--branch', 'main']):
            with self.subTest(options=options):
                result = subprocess.run(['bash', str(SCRIPT), *options],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('error:', result.stderr)
                self.assertNotIn('Fetching', result.stdout)

    def exercise_update(self, release=None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / 'remote'
            payload = repo / 'desktop/payload'
            source = payload / 'home/.config/quickshell/shell.qml'
            source.parent.mkdir(parents=True)
            source.write_text('release source')
            preference = payload / 'home/.config/rebos_shell/config/theme.json'
            preference.parent.mkdir(parents=True)
            preference.write_text('{"theme":"default"}')
            (payload / 'manifest.json').write_text(json.dumps({'units': [
                '.config/quickshell', '.config/rebos_shell/config/theme.json']}))
            hashes = {str(p.relative_to(payload)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in payload.rglob('*') if p.is_file()}
            (payload / 'checksums.json').write_text(json.dumps(hashes))
            setup = repo / 'desktop/scripts/greeter_sync.py'
            setup.parent.mkdir(parents=True)
            setup.write_text("from pathlib import Path\n(Path.home() / 'greeter-refreshed').write_text('yes')\n")
            def git(*args):
                subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)
            git('init')
            git('add', '.')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-m', 'snapshot')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.com',
                'tag', '-a', 'v1.3.0', '-m', 'Release')
            source.write_text('latest source')
            hashes[str(source.relative_to(payload))] = hashlib.sha256(source.read_bytes()).hexdigest()
            (payload / 'checksums.json').write_text(json.dumps(hashes))
            git('add', '.')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-m', 'After release')
            git('branch', 'v1.3.0')
            git('branch', 'v9.9.9')
            home = root / 'home'
            existing = home / '.config/rebos_shell/config/theme.json'
            existing.parent.mkdir(parents=True)
            existing.write_text('{"theme":"personal"}')
            environment = dict(os.environ, HOME=str(home))
            for key in ['XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME']:
                environment.pop(key, None)
            command = ['bash', str(SCRIPT), '--repository', str(repo), '--files-only']
            if release:
                command += ['--release', release]
            preview = subprocess.run(command + ['--dry-run'], env=environment, capture_output=True, text=True)
            if release == 'v9.9.9':
                self.assertNotEqual(preview.returncode, 0)
                self.assertFalse((home / '.config/quickshell').exists())
                self.assertFalse((home / '.local/state/rebos-desktop').exists())
                self.assertFalse((home / 'greeter-refreshed').exists())
                self.assertEqual(existing.read_text(), '{"theme":"personal"}')
                return
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertFalse((home / '.config/quickshell').exists())
            self.assertFalse((home / 'greeter-refreshed').exists())
            for _ in range(2):
                result = subprocess.run(command, env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((home / 'greeter-refreshed').read_text(), 'yes')
                self.assertEqual(existing.read_text(), '{"theme":"personal"}')
                self.assertEqual((home / '.config/quickshell/shell.qml').read_text(),
                                 'release source' if release else 'latest source')
            self.assertEqual(len(list((home / '.local/state/rebos-desktop/backups').iterdir())), 2)
