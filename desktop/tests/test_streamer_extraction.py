import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2] / 'system/apps/media'

class StandaloneTests(unittest.TestCase):
    def test_installer_uses_checkout_and_never_restarts_playback(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            bindir = home / 'bin'
            bindir.mkdir()
            fake = bindir / 'systemctl'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" > "$HOME/systemctl-call"\n')
            fake.chmod(0o755)
            subprocess.run(['python3', str(ROOT / 'install.py')], check=True,
                           env={**os.environ, 'HOME': temp, 'PATH': str(bindir) + ':' + os.environ['PATH']}, capture_output=True)
            self.assertEqual((home / 'systemctl-call').read_text().strip(), '--user daemon-reload')
            unit = (home / '.config/systemd/user/anime-streamer.service').read_text()
            self.assertIn(str(ROOT / 'backend_server.py'), unit)
            self.assertIn(str(ROOT / 'launch'), (home / '.local/bin/anime-streamer').read_text())

    def test_ui_has_no_installed_shell_dependency(self):
        for path in (ROOT / 'ui').rglob('*.qml'):
            self.assertNotIn('/.config/quickshell', path.read_text())
        self.assertTrue((ROOT / 'vendor/ani-cli').is_file())
