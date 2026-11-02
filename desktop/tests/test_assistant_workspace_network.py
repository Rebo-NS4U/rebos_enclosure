"""Exercise network configuration through the real launcher/process boundary."""
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'payload/home/code/rebos-assistant'

NATIVE = r'''#!/usr/bin/env python3
import json, signal, sys
if '--wait' in sys.argv:
    print('ready', flush=True)
    signal.pause()
elif '--exit' in sys.argv:
    sys.exit(23)
elif '--show-args' in sys.argv:
    print(json.dumps(sys.argv[1:]))
else:
    for line in sys.stdin.buffer:
        sys.stdout.buffer.write(line)
        sys.stdout.buffer.flush()
'''


class AssistantWorkspaceNetworkTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='assistant-workspace-network-')
        self.addCleanup(self.temporary.cleanup)
        binary = Path(self.temporary.name) / 'codex'
        binary.write_text(NATIVE)
        binary.chmod(0o755)
        self.command = [sys.executable, str(ROOT / 'scripts/codex_workspace.py')]
        self.environment = dict(os.environ, REBOS_CODEX_BINARY=str(binary), CODEX_CONFIG=json.dumps({
            'sandbox_workspace_write': {'network_access': True}}))

    def run_launcher(self, payload=b'', args=('app-server',), config=None):
        environment = self.environment.copy()
        if config is not None:
            environment['CODEX_CONFIG'] = config
        return subprocess.run([*self.command, *args], input=payload, env=environment,
                              capture_output=True, timeout=5)

    def test_network_enabled_without_changing_filesystem_or_approvals(self):
        policy = dict(type='workspaceWrite', networkAccess=False,
                      writableRoots=['/workspace'], excludeTmpdirEnvVar=True, excludeSlashTmp=True)
        original = dict(id=9, method='turn/start', params=dict(
            threadId='thread', approvalPolicy='on-request', approvalsReviewer='user',
            sandboxPolicy=policy, input=[{'type': 'text', 'text': 'Check GitHub'}]))
        result = self.run_launcher((json.dumps(original) + '\n').encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertTrue(actual['params']['sandboxPolicy']['networkAccess'])
        actual['params']['sandboxPolicy']['networkAccess'] = False
        self.assertEqual(actual, original)

    def test_other_modes_protocol_frames_and_output_are_unchanged(self):
        frames = [dict(id=1, method='initialize', params={}),
                  dict(id=2, method='thread/start', params={'sandbox': 'workspace-write'}),
                  dict(id=3, method='turn/start', params={}),
                  dict(id=4, result={'accepted': True})]
        for policy in ({'type': 'readOnly', 'networkAccess': False},
                       {'type': 'dangerFullAccess'}, {'type': 'futurePolicy'},
                       {'type': 'workspaceWrite', 'networkAccess': True}):
            frames.append(dict(method='turn/start', params={'sandboxPolicy': policy}))
        payload = ''.join(json.dumps(frame) + '\n' for frame in frames).encode() + b'invalid-json\n'
        result = self.run_launcher(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, payload)

    def test_network_requires_explicit_boolean_opt_in(self):
        payload = b'{"method":"turn/start","params":{"sandboxPolicy":{"type":"workspaceWrite","networkAccess":false}}}\n'
        for config in ({}, {'sandbox_workspace_write': {'network_access': False}},
                       {'sandbox_workspace_write': {'network_access': 'true'}}):
            with self.subTest(config=config):
                result = self.run_launcher(payload, config=json.dumps(config))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, payload)

    def test_cli_and_app_server_arguments_and_exit_status_are_preserved(self):
        for args in (('app-server', '-c', 'hooks={}', '--show-args'), ('login', '--show-args')):
            result = self.run_launcher(args=args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), list(args))
        self.assertEqual(self.run_launcher(args=('app-server', '--exit')).returncode, 23)

    def test_invalid_configuration_fails_before_launch(self):
        result = self.run_launcher(config='invalid-json')
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'CODEX_CONFIG is invalid JSON', result.stderr)
        self.assertEqual(result.stdout, b'')

    def test_termination_reaches_child(self):
        process = subprocess.Popen([*self.command, 'app-server', '--wait'],
                                   env=self.environment, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertTrue(select.select([process.stdout], [], [], 3)[0], 'server did not start')
            self.assertEqual(process.stdout.readline(), b'ready\n')
            process.terminate()
            _, error = process.communicate(timeout=3)
            self.assertEqual(process.returncode, 143, error)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()


if __name__ == '__main__':
    unittest.main()
