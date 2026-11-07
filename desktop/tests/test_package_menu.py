"""Verify packaged update launchers without installing packages."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class PackageMenuTests(unittest.TestCase):
    def test_update_preview_and_failure_reporting(self):
        scripts = Path(__file__).resolve().parents[2] / 'system/scripts'
        with tempfile.TemporaryDirectory() as folder:
            tools = Path(folder)
            for name in ('paru', 'flatpak', 'rustup'):
                tool = tools / name
                tool.write_text('#!/bin/sh\nprintf "invoked:%s\\n" "$0"\nexit 1\n')
                tool.chmod(0o755)
            env = dict(os.environ, PATH=folder + ':/usr/bin', HOME=folder)
            command = ['bash', str(scripts / 'package-menu.sh'), '--update']
            preview = subprocess.run(command + ['--dry-run'], env=env, capture_output=True, text=True)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertIn('--nosudoloop -Syu --devel --noconfirm', preview.stdout)
            self.assertIn('--skipreview --noupgrademenu', preview.stdout)
            self.assertIn('flatpak update --system', preview.stdout)
            self.assertIn('flatpak update --user', preview.stdout)
            self.assertIn('rustup update --no-self-update', preview.stdout)
            self.assertNotIn('invoked:', preview.stdout)
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Arch/AUR update failed', result.stderr)
            self.assertIn('Rust toolchain update failed', result.stderr)

    def test_keyring_repair_retries_once_and_other_errors_stop(self):
        source = Path(__file__).resolve().parents[2] / 'system/scripts/package-menu.sh'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            menu = root / 'package-menu.sh'
            menu.write_text(source.read_text())
            admin = root / 'package-admin.sh'
            admin.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$HOME/calls"\nexit 0\n')
            admin.chmod(0o755)
            helper = root / 'paru'
            helper.write_text('#!/bin/bash\nprintf "helper\\n" >> "$HOME/calls"\necho "$FAILURE"\nexit 1\n')
            helper.chmod(0o755)
            # Restrict discovery to mock helper and the basic utilities it needs.
            for name in ('bash', 'mktemp', 'tee', 'grep', 'rm', 'dirname'):
                (root / name).symlink_to('/usr/bin/' + name)
            env = dict(os.environ, HOME=folder, PATH=folder)
            for failure, attempts in [('signature from key is unknown trust', 2),
                                      ('failed to lock database', 1)]:
                with self.subTest(failure=failure):
                    calls = root / 'calls'
                    calls.unlink(missing_ok=True)
                    result = subprocess.run(['/usr/bin/bash', str(menu), '--update'],
                                            env=dict(env, FAILURE=failure), capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    lines = calls.read_text().splitlines()
                    self.assertEqual(lines.count('helper'), attempts)
                    self.assertEqual(any('archlinux-keyring' in line for line in lines), attempts == 2)

    def test_compatibility_launchers_find_shared_menu(self):
        scripts = Path(__file__).resolve().parents[2] / 'system/scripts'
        for name in ('install.sh', 'install-aur.sh', 'uninstall.sh'):
            result = subprocess.run(['bash', str(scripts / name), '--help'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('package-menu.sh', result.stdout)
