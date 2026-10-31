"""Exercise remote fetching and preference preservation without touching the desktop."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'update.sh'


@unittest.skipIf(os.geteuid() == 0, 'Updater intentionally refuses root')
class UpdateTests(unittest.TestCase):
    def test_fetch_preview_apply_and_repeat(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / 'remote'
            payload = repo / 'desktop/payload'
            source = payload / 'home/.config/quickshell/shell.qml'
            source.parent.mkdir(parents=True)
            source.write_text('latest source')
            preference = payload / 'home/.config/rebos_shell/config/theme.json'
            preference.parent.mkdir(parents=True)
            preference.write_text('{"theme":"default"}')
            (payload / 'manifest.json').write_text(json.dumps({'units': [
                '.config/quickshell', '.config/rebos_shell/config/theme.json']}))
            hashes = {str(p.relative_to(payload)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in payload.rglob('*') if p.is_file()}
            (payload / 'checksums.json').write_text(json.dumps(hashes))
            def git(*args):
                subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)
            git('init')
            git('add', '.')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-m', 'snapshot')
            home = root / 'home'
            existing = home / '.config/rebos_shell/config/theme.json'
            existing.parent.mkdir(parents=True)
            existing.write_text('{"theme":"personal"}')
            environment = dict(os.environ, HOME=str(home))
            for key in ['XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME']:
                environment.pop(key, None)
            command = ['bash', str(SCRIPT), '--repository', str(repo), '--files-only']
            preview = subprocess.run(command + ['--dry-run'], env=environment, capture_output=True, text=True)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertFalse((home / '.config/quickshell').exists())
            for _ in range(2):
                result = subprocess.run(command, env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(existing.read_text(), '{"theme":"personal"}')
                self.assertEqual((home / '.config/quickshell/shell.qml').read_text(), 'latest source')
            self.assertEqual(len(list((home / '.local/state/rebos-desktop/backups').iterdir())), 2)
