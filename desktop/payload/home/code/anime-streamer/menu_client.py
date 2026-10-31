#!/usr/bin/env python3
"""Short-lived QuickShell transport to the persistent playback service."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time


def main():
    result = subprocess.run(['systemctl', '--user', 'start', 'anime-streamer.service'], capture_output=True, timeout=15)
    if result.returncode:
        print(json.dumps(dict(event='error', text='Could not start the anime playback service')), flush=True)
        return 1
    path = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp')) / f'anime-streamer-{os.getuid()}.sock'
    connection = socket.socket(socket.AF_UNIX)
    for _ in range(100):
        try:
            connection.connect(str(path))
            break
        except OSError:
            time.sleep(.05)
    else:
        raise RuntimeError('Anime playback service did not become ready')
    def requests():
        try:
            for line in sys.stdin.buffer:
                connection.sendall(line)
        except OSError:
            pass
        finally:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
    threading.Thread(target=requests, daemon=True).start()
    try:
        with connection, connection.makefile('rb') as stream:
            for line in stream:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
    except (OSError, BrokenPipeError):
        pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
