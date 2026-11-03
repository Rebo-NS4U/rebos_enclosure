"""Exercise connection repair through real Git and a fake GitHub CLI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts'
sys.path.insert(0, str(SCRIPTS))
import github_connect

CLI = '''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
args = sys.argv[1:]
home = pathlib.Path.home()
with (home / 'gh-calls').open('a') as log: log.write(json.dumps(args) + '\\n')
if args[0] == 'api':
 mode = os.environ.get('TEST_GH_MODE', '')
 if mode == 'network':
  print('error connecting to api.github.com; try gh auth login', file=sys.stderr); sys.exit(1)
 if mode == 'auth' and not (home / 'logged-in').exists():
  print('HTTP 401: Bad credentials', file=sys.stderr); sys.exit(1)
 print(json.dumps({'login':'test-user', 'id':123, 'name':'Test User'}))
elif args[:2] == ['auth','login']:
 (home / 'logged-in').touch()
elif args[:2] == ['auth','setup-git']:
 subprocess.run(['git','config','--global','credential.https://github.com.helper', '!gh auth git-credential'], check=True)
'''


class ConnectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.repo = self.home / 'project'
        self.repo.mkdir()
        binary = self.home / 'bin'
        binary.mkdir()
        (binary / 'gh').write_text(CLI)
        (binary / 'gh').chmod(0o755)
        env = dict(HOME=str(self.home), GIT_CONFIG_GLOBAL=str(self.home / '.gitconfig'),
                   GIT_CONFIG_NOSYSTEM='1', PATH=str(binary) + ':' + os.environ['PATH'], TEST_GH_MODE='')
        self.environment = patch.dict(os.environ, env)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.git('init', '-q')
        self.git('remote', 'add', 'origin', 'https://github.com/test-user/project.git')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def calls(self):
        return [json.loads(line) for line in (self.home / 'gh-calls').read_text().splitlines()]

    def test_connect_configures_helper_and_missing_identity_idempotently(self):
        github_connect.connect(self.repo)
        first = (self.repo / '.git/config').read_bytes()
        self.assertEqual(self.git('config', 'user.name'), 'Test User')
        self.assertEqual(self.git('config', 'user.email'), '123+test-user@users.noreply.github.com')
        self.assertEqual(self.git('config', '--global', 'credential.https://github.com.helper'), '!gh auth git-credential')
        github_connect.connect(self.repo)
        self.assertEqual((self.repo / '.git/config').read_bytes(), first)
        self.assertNotIn(['auth', 'login'], [call[:2] for call in self.calls()])

    def test_existing_author_preferences_are_preserved(self):
        self.git('config', '--global', 'user.name', 'Chosen Name')
        self.git('config', '--local', 'user.email', 'chosen@example.invalid')
        github_connect.connect(self.repo)
        self.assertEqual(self.git('config', 'user.name'), 'Chosen Name')
        self.assertEqual(self.git('config', 'user.email'), 'chosen@example.invalid')
        result = subprocess.run(['git', '-C', str(self.repo), 'config', '--local', '--get', 'user.name'], capture_output=True)
        self.assertEqual(result.returncode, 1)

    def test_network_failure_does_not_reauthenticate_or_modify_config(self):
        os.environ['TEST_GH_MODE'] = 'network'
        original = (self.repo / '.git/config').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Cannot reach GitHub'):
            github_connect.connect(self.repo, login=True)
        self.assertEqual((self.repo / '.git/config').read_bytes(), original)
        self.assertEqual(len(self.calls()), 1)
        self.assertFalse((self.home / '.gitconfig').exists())

    def test_confirmed_auth_failure_can_login_then_configure_git(self):
        os.environ['TEST_GH_MODE'] = 'auth'
        github_connect.connect(self.repo, login=True)
        self.assertTrue((self.home / 'logged-in').exists())
        self.assertEqual([call[:2] for call in self.calls()],
                         [['api', '--hostname'], ['auth', 'login'], ['api', '--hostname'], ['auth', 'setup-git']])

    def test_auth_failure_without_login_flag_is_read_only(self):
        os.environ['TEST_GH_MODE'] = 'auth'
        with self.assertRaisesRegex(ValueError, '401'):
            github_connect.connect(self.repo)
        self.assertEqual(len(self.calls()), 1)


if __name__ == '__main__':
    unittest.main()
