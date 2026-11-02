"""Check private credentials and provider routing at the process boundary."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'payload/home/code/rebos-assistant/scripts/openrouter_agent.py'
spec = importlib.util.spec_from_file_location('openrouter_agent', SCRIPT)
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)


class OpenRouterTest(unittest.TestCase):
    def test_provider_overrides_preserve_permissions_and_shared_config(self):
        original = {'approval_policy': 'on-request', 'sandbox_workspace_write': {'network_access': False},
                    'features': {'shell_tool': True}, 'model_providers': {'other': {'name': 'Other'}}}
        for selection in agent.MODELS:
            env = agent.launch_environment(selection, {'OPENROUTER_API_KEY': 'test-only', 'CODEX_CONFIG': json.dumps(original)})
            config = json.loads(env['CODEX_CONFIG'])
            self.assertEqual(config['approval_policy'], original['approval_policy'])
            self.assertEqual(config['sandbox_workspace_write'], original['sandbox_workspace_write'])
            self.assertTrue(config['features']['shell_tool'])
            self.assertEqual(config['model_providers']['other'], original['model_providers']['other'])
            self.assertEqual(config['model'], agent.MODELS[selection])
            provider = config['model_providers'][config['model_provider']]
            self.assertEqual(provider['wire_api'], 'responses')
            self.assertFalse(provider['requires_openai_auth'])
            self.assertNotIn('test-only', env['CODEX_CONFIG'])

    def test_private_file_and_missing_key(self):
        with tempfile.TemporaryDirectory() as temp:
            env = {'XDG_CONFIG_HOME': temp}
            with self.assertRaisesRegex(ValueError, 'Create'):
                agent.launch_environment('free-code', env)
            path = Path(temp) / 'dweebo/openrouter-api-key'
            path.parent.mkdir()
            path.write_text('test-only\n')
            path.chmod(0o644)
            with self.assertRaisesRegex(ValueError, '600'):
                agent.launch_environment('free-code', env)
            path.chmod(0o600)
            self.assertEqual(agent.launch_environment('free-code', env)['OPENROUTER_API_KEY'], 'test-only')

    def test_catalog_contains_both_free_models_without_openai_defaults(self):
        env = agent.launch_environment('free-code', {'OPENROUTER_API_KEY': 'test-only'})
        config = json.loads(env['CODEX_CONFIG'])
        catalog = json.loads(Path(config['model_catalog_json']).read_text())
        self.assertEqual({model['slug'] for model in catalog['models']}, set(agent.MODELS.values()))
        for model in catalog['models']:
            self.assertEqual(model['input_modalities'], ['text'])
            self.assertFalse(model['use_responses_lite'])
            self.assertGreater(model['context_window'], 0)
            self.assertIn('Respond to greetings naturally', model['model_messages']['instructions_template'])

    def test_invalid_configuration(self):
        for config in ('[]', 'null', '{'):
            with self.assertRaises(ValueError):
                agent.launch_environment('free-code', {'OPENROUTER_API_KEY': 'test-only', 'CODEX_CONFIG': config})

    def test_launch_executes_acp_with_scoped_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / 'npx'
            binary.write_text('#!' + sys.executable + '\nimport json,os,sys\nprint(json.dumps({"args":sys.argv[1:],"provider":os.environ["MODEL_PROVIDER"],"config":json.loads(os.environ["CODEX_CONFIG"])}))\n')
            binary.chmod(0o755)
            env = dict(os.environ, PATH=temp + ':' + os.environ['PATH'], OPENROUTER_API_KEY='test-only', CODEX_CONFIG='{}')
            result = subprocess.run([sys.executable, str(SCRIPT), 'free-code'], env=env, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            actual = json.loads(result.stdout)
            self.assertEqual(actual['args'], ['-y', '@agentclientprotocol/codex-acp'])
            self.assertEqual(actual['provider'], 'dweebo_openrouter')
            invalid = subprocess.run([sys.executable, str(SCRIPT), 'unknown'], env=env, capture_output=True)
            self.assertEqual(invalid.returncode, 2)
