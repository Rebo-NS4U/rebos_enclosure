#!/usr/bin/env python3
"""QuickShell transport that survives playback service restarts."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import time


@dataclass(frozen=True)
class RelayIO:
    path: Path
    input_fd: int
    output: object
    retry_delay: float


class MenuRelay:
    def __init__(self, transport):
        self.io = transport
        self.connection = None
        self.retry_at = 0
        self.notified = False
        self.pending = b''

    def notify_lost(self):
        self.io.output.write(b'{"event":"connection-lost"}\n')
        self.io.output.flush()
        self.notified = True

    def connect(self):
        candidate = socket.socket(socket.AF_UNIX)
        try:
            candidate.connect(str(self.io.path))
        except OSError:
            candidate.close()
            self.retry_at = time.monotonic() + self.io.retry_delay
            if not self.notified:
                self.notify_lost()
        else:
            self.connection = candidate
            self.notified = False

    def disconnect(self, retry_at):
        self.connection.close()
        self.connection = None
        self.pending = b''
        self.retry_at = retry_at
        self.notify_lost()

    def read_socket(self):
        try:
            data = self.connection.recv(65536)
        except OSError:
            data = b''
        if not data:
            self.disconnect(time.monotonic() + self.io.retry_delay)
            return
        self.pending += data
        while b'\n' in self.pending:
            line, self.pending = self.pending.split(b'\n', 1)
            self.io.output.write(line + b'\n')
            self.io.output.flush()

    def read_input(self):
        data = os.read(self.io.input_fd, 65536)
        if not data:
            return False
        if self.connection is not None:
            try:
                self.connection.sendall(data)
            except OSError:
                self.disconnect(0)
        # Never replay commands issued during an outage.
        return True

    def run(self):
        try:
            while True:
                if self.connection is None and time.monotonic() >= self.retry_at:
                    self.connect()
                readers = [self.io.input_fd] + ([self.connection] if self.connection is not None else [])
                readable, _, _ = select.select(readers, [], [], self.io.retry_delay)
                # EOF must be announced before processing further input.
                if self.connection is not None and self.connection in readable:
                    self.read_socket()
                if self.io.input_fd in readable and not self.read_input():
                    return 0
        except (BrokenPipeError, ConnectionResetError):
            return 0
        finally:
            if self.connection is not None:
                self.connection.close()


def relay(path, input_fd, output, retry_delay=1):
    """Reconnect without replaying commands or owning playback lifetime."""
    return MenuRelay(RelayIO(path, input_fd, output, retry_delay)).run()


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
