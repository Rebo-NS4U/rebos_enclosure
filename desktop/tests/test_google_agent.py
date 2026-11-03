"""Verify Google credentials and the native ACP launcher at process boundaries."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'system/apps/assistant/scripts/google_agent.py'
spec = importlib.util.spec_from_file_location('google_agent', SCRIPT)
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)


class GoogleAgentTest(unittest.TestCase):
    def test_environment_aliases_and_isolated_cli_home(self):
        with tempfile.TemporaryDirectory() as temporary:
            for name in agent.KEY_NAMES:
                env = agent.launch_environment({name: 'test-only', 'XDG_CONFIG_HOME': temporary,
                                                'XDG_DATA_HOME': temporary + '/data'})
                self.assertEqual(env['GEMINI_API_KEY'], 'test-only')
                self.assertEqual(env['GEMINI_CLI_HOME'], temporary + '/data/dweebo/google')
                self.assertEqual(env['GEMINI_TELEMETRY_ENABLED'], 'false')
                settings = json.loads(Path(env['GEMINI_CLI_SYSTEM_SETTINGS_PATH']).read_text())
                self.assertEqual(settings['general']['maxAttempts'], 1)
                self.assertFalse(settings['general']['retryFetchErrors'])
                self.assertFalse(settings['general']['plan']['modelRouting'])

    def test_file_permissions_missing_key_and_rotation(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = {'XDG_CONFIG_HOME': temporary}
            with self.assertRaisesRegex(ValueError, 'google-api-key'):
                agent.launch_environment(env)
            path = Path(temporary) / 'dweebo/google-api-key'
            path.parent.mkdir()
            path.write_text('replacement-test-key\n')
            path.chmod(0o644)
            with self.assertRaisesRegex(ValueError, '600'):
                agent.launch_environment(env)
            path.chmod(0o600)
            result = agent.launch_environment({**env, 'GEMINI_API_KEY': 'old-test-key'})
            self.assertEqual(result['GEMINI_API_KEY'], 'replacement-test-key')

    def test_save_key_import_and_hidden_prompt_preserve_symlink_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = {'XDG_CONFIG_HOME': temporary, 'GOOGLE_API_KEY': 'test-import'}
            path = agent.save_key(env, prompt=lambda _: self.fail('exported key should not prompt'))
            self.assertEqual(path.read_text(), 'test-import\n')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            target = Path(temporary) / 'private-key-target'
            target.write_text('old')
            path.unlink()
            path.symlink_to(target)
            agent.save_key({'XDG_CONFIG_HOME': temporary}, prompt=lambda _: 'replacement-test')
            self.assertTrue(path.is_symlink())
            self.assertEqual(target.read_text(), 'replacement-test\n')
            with self.assertRaises(ValueError):
                agent.save_key({'XDG_CONFIG_HOME': temporary}, prompt=lambda _: '')
            self.assertEqual(target.read_text(), 'replacement-test\n')

    def test_exec_uses_native_acp_and_default_permissions(self):
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary) / 'npx'
            binary.write_text('#!' + sys.executable + '\nimport json,os,sys\n'
                              'print(json.dumps({"args":sys.argv[1:],"keyPresent":bool(os.environ.get("GEMINI_API_KEY")),"cliHome":os.environ.get("GEMINI_CLI_HOME")}))\n')
            binary.chmod(0o755)
            env = dict(os.environ, PATH=temporary + ':' + os.environ['PATH'],
                       GEMINI_API_KEY='test-only', XDG_CONFIG_HOME=temporary, XDG_DATA_HOME=temporary)
            result = subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data['keyPresent'])
            self.assertEqual(data['args'], ['-y', agent.GEMINI_PACKAGE, '--acp', '--model', agent.GOOGLE_MODEL, '--approval-mode', 'default'])
            self.assertNotIn(b'test-only', result.stdout)
            self.assertNotIn('--yolo', data['args'])


if __name__ == '__main__':
    unittest.main()
