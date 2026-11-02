#!/usr/bin/env python3
"""QuickShell transport that survives playback service restarts."""
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import time


def relay(path, input_fd, output, retry_delay=1):
    """Reconnect without replaying playback commands or owning playback lifetime."""
    connection = None
    retry_at = 0
    notified = False
    pending = b''
    try:
        while True:
            if connection is None and time.monotonic() >= retry_at:
                candidate = socket.socket(socket.AF_UNIX)
                try:
                    candidate.connect(str(path))
                except OSError:
                    candidate.close()
                    retry_at = time.monotonic() + retry_delay
                    if not notified:
                        output.write(b'{"event":"connection-lost"}\n')
                        output.flush()
                        notified = True
                else:
                    connection = candidate
                    notified = False
            readers = [input_fd] + ([connection] if connection is not None else [])
            readable, _, _ = select.select(readers, [], [], retry_delay)
            # Drain socket events first so EOF is announced before further commands.
            if connection is not None and connection in readable:
                try:
                    data = connection.recv(65536)
                except OSError:
                    data = b''
                if data:
                    pending += data
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        output.write(line + b'\n')
                        output.flush()
                else:
                    connection.close()
                    connection = None
                    pending = b''
                    retry_at = time.monotonic() + retry_delay
                    output.write(b'{"event":"connection-lost"}\n')
                    output.flush()
                    notified = True
            if input_fd in readable:
                data = os.read(input_fd, 65536)
                if not data:
                    return 0
                if connection is not None:
                    try:
                        connection.sendall(data)
                    except OSError:
                        connection.close()
                        connection = None
                        pending = b''
                        retry_at = 0
                        output.write(b'{"event":"connection-lost"}\n')
                        output.flush()
                        notified = True
                # Never replay commands issued during an outage.
    except (BrokenPipeError, ConnectionResetError):
        return 0
    finally:
        if connection is not None:
            connection.close()


def main():
    try:
        result = subprocess.run(['systemctl', '--user', 'start', 'anime-streamer.service'],
                                capture_output=True, timeout=15)
        if result.returncode:
            raise RuntimeError('Could not start the playback service')
    except (OSError, subprocess.SubprocessError, RuntimeError):
        print(json.dumps(dict(event='error', text='Could not start the playback service')), flush=True)
        return 1
    path = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp')) / f'anime-streamer-{os.getuid()}.sock'
    return relay(path, sys.stdin.fileno(), sys.stdout.buffer)


if __name__ == '__main__':
    raise SystemExit(main())
