"""Exercise panel discovery and supervision without touching the live session."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / 'payload/home'


class PanelStartupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rebos-panel-test-')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / 'user home'
        self.home.mkdir()
        commands = self.home / 'bin'
        commands.mkdir()
        shell = self.home / '.config/quickshell'
        shell.mkdir(parents=True)
        (shell / 'shell.qml').touch()
        self.log = self.home / 'systemctl.log'
        self.env = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / '.config'),
                        XDG_STATE_HOME=str(self.home / '.local/state'),
                        XDG_DATA_HOME=str(self.home / '.local/share'),
                        PATH=str(commands) + ':' + os.environ['PATH'], PANEL_TEST_LOG=str(self.log))
        for name, body in {
            'qs': 'printf "%s\\n" "$PANEL_TEST_INSTANCES"',
            'systemctl': 'printf "%s\\n" "$*" >> "$PANEL_TEST_LOG"',
        }.items():
            path = commands / name
            path.write_text('#!/usr/bin/env bash\nset -euo pipefail\n' + body + '\n')
            path.chmod(0o755)

    def rice(self, action, instances):
        env = dict(self.env, PANEL_TEST_INSTANCES=instances)
        return subprocess.run(['bash', str(PAYLOAD / '.local/bin/rice'), action],
                              env=env, check=True, capture_output=True, text=True)

    def test_assistant_does_not_suppress_panel_start(self):
        instances = f'  Process ID: 22\n  Config path: {self.home}/code/rebos-assistant/shell.qml\n'
        self.assertIn('stopped', self.rice('status', instances).stdout)
        self.rice('start', instances)
        self.assertIn('--user start rebos-panel.service', self.log.read_text())

    def test_existing_panel_uses_registry_instead_of_process_name(self):
        instances = f'  Process ID: 31\n  Config path: {self.home}/.config/quickshell/shell.qml\n'
        self.assertIn('running', self.rice('status', instances).stdout)
        self.rice('start', instances)
        self.assertFalse(self.log.exists())

    def test_unsupported_qt_never_builds_or_writes_guard(self):
        pkg = self.home / 'bin/pkg-config'
        pkg.write_text('#!/bin/sh\nprintf "6.13.0\\n"\n')
        pkg.chmod(0o755)
        subprocess.run(['bash', str(PAYLOAD / '.config/quickshell/scripts/build_qt_screen_guard.sh')],
                       env=self.env, check=True, capture_output=True)
        self.assertFalse((self.home / '.local/share').exists())


if __name__ == '__main__':
    unittest.main()
