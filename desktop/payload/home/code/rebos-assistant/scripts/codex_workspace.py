#!/usr/bin/env python3
"""Honor Dweebo's workspace network config at the ACP/app-server boundary.

codex-acp supplies a network-disabled workspace sandbox on every turn, overriding
the standard sandbox_workspace_write.network_access configuration. Carry that
explicit configuration into workspace turns without changing filesystem roots,
read-only mode, approval policies, responses, or other app-server requests.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading


def workspace_network_enabled(environment):
    config = json.loads(environment.get('CODEX_CONFIG', '{}'))
    workspace = config.get('sandbox_workspace_write', {}) if isinstance(config, dict) else {}
    return isinstance(workspace, dict) and workspace.get('network_access') is True


def workspace_request(line):
    try:
        request = json.loads(line)
    except (ValueError, UnicodeError):
        return line
    if not isinstance(request, dict) or request.get('method') != 'turn/start':
        return line
    params = request.get('params')
    policy = params.get('sandboxPolicy') if isinstance(params, dict) else None
    if not isinstance(policy, dict) or policy.get('type') != 'workspaceWrite':
        return line
    if policy.get('networkAccess') is True:
        return line
    policy['networkAccess'] = True
    return (json.dumps(request, separators=(',', ':')) + '\n').encode()


def main():
    binary = os.environ.get('REBOS_CODEX_BINARY') or shutil.which('codex')
    if not binary or Path(binary).resolve() == Path(__file__).resolve():
        sys.stderr.write('Dweebo could not locate the native Codex executable.\n')
        return 1
    try:
        enabled = workspace_network_enabled(os.environ)
    except ValueError:
        sys.stderr.write('Dweebo CODEX_CONFIG is invalid JSON.\n')
        return 1
    arguments = sys.argv[1:]
    if not enabled or not arguments or arguments[0] != 'app-server':
        os.execv(binary, [binary, *arguments])
    # stdout/stderr are inherited unchanged, including the adapter's JSON stream.
    process = subprocess.Popen([binary, *arguments], stdin=subprocess.PIPE)

    def forward_input():
        try:
            for line in sys.stdin.buffer:
                process.stdin.write(workspace_request(line))
                process.stdin.flush()
        except BrokenPipeError:
            pass
        finally:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass

    def forward_signal(number, _frame):
        try:
            process.send_signal(number)
        except ProcessLookupError:
            pass

    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(number, forward_signal)
    # Wait independently so an app-server crash cannot leave the wrapper stuck
    # reading adapter input. EOF still reaches the server as normal.
    threading.Thread(target=forward_input, daemon=True).start()
    result = process.wait()
    return result if result >= 0 else 128 - result


if __name__ == '__main__':
    raise SystemExit(main())
