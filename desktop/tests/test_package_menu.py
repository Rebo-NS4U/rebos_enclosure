"""Verify packaged update launchers without installing packages."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class PackageMenuTests(unittest.TestCase):
    def test_update_preview_and_failure_reporting(self):
        scripts = Path(__file__).resolve().parents[1] / 'payload/home/.config/scripts'
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
            self.assertIn('--nosudoloop -Syu --devel', preview.stdout)
            self.assertIn('flatpak update --system', preview.stdout)
            self.assertIn('flatpak update --user', preview.stdout)
            self.assertIn('rustup update --no-self-update', preview.stdout)
            self.assertNotIn('invoked:', preview.stdout)
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Arch/AUR update failed', result.stderr)
            self.assertIn('Rust toolchain update failed', result.stderr)

    def test_compatibility_launchers_find_shared_menu(self):
        scripts = Path(__file__).resolve().parents[1] / 'payload/home/.config/scripts'
        for name in ('install.sh', 'install-aur.sh', 'uninstall.sh'):
            result = subprocess.run(['bash', str(scripts / name), '--help'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('package-menu.sh', result.stdout)
