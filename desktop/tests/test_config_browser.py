"""Run the configuration menu with recording UI/open helpers, without a desktop."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'system/bin/config-browser'


class ConfigBrowserTests(unittest.TestCase):
    def test_personal_and_system_locations_are_distinct_menu_choices(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            commands = home / 'bin'
            commands.mkdir()
            for relative in ('.config/enclosure/niri', '.local/share/enclosure/system/apps', '.local/share/enclosure/defaults'):
                (home / relative).mkdir(parents=True)
            zenity = commands / 'zenity'
            zenity.write_text('#!' + sys.executable + '\nimport json,os,sys\nfrom pathlib import Path\n'
                'Path(os.environ["MENU_LOG"]).write_text(json.dumps(sys.argv[1:]))\n'
                'print("Personal settings — all applications")\n')
            opener = commands / 'xdg-open'
            opener.write_text('#!' + sys.executable + '\nimport os,sys\nfrom pathlib import Path\n'
                'Path(os.environ["OPEN_LOG"]).write_text(sys.argv[1])\n')
            zenity.chmod(0o755)
            opener.chmod(0o755)
            log, opened = home / 'menu.json', home / 'opened.txt'
            env = {**os.environ, 'HOME': str(home), 'PATH': str(commands) + ':/usr/bin',
                   'MENU_LOG': str(log), 'OPEN_LOG': str(opened)}
            result = subprocess.run(['bash', str(SCRIPT)], env=env, text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            args = json.loads(log.read_text())
            self.assertIn('Personal settings — all applications', args)
            self.assertIn('System — configuration defaults (replaced by updates)', args)
            self.assertIn('System — managed applications and services', args)
            deadline = time.monotonic() + 2
            while not opened.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(opened.read_text(), str(home / '.config/enclosure'))


if __name__ == '__main__':
    unittest.main()
