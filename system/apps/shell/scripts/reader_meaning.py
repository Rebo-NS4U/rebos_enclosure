#!/usr/bin/env python3
"""Request a bounded passage explanation through the configured assistant UI."""
import json
from pathlib import Path
import re
import signal
import subprocess
import sys
import time


def ipc(action, value, runner=subprocess.run):
    result = runner(['qs', 'ipc', '-p', str(Path.home() / 'code/rebos-assistant'),
                     'call', 'assistant', action, value], capture_output=True, text=True,
                    timeout=5, check=True)
    return json.loads(result.stdout)


def lookup(payload, runner=subprocess.run, call=ipc, sleep=time.sleep, clock=time.monotonic):
    if not isinstance(payload, dict): raise ValueError('Expected a lookup request.')
    token = payload.get('token', '')
    if (not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', token)
            or not isinstance(payload.get('term'), str) or not 0 < len(payload['term']) <= 128
            or not isinstance(payload.get('context'), str) or not 0 < len(payload['context']) <= 1000):
        raise ValueError('Select a word in the current passage first.')
    runner(['systemctl', '--user', 'start', 'rebos-assistant-ui.service'],
           check=True, capture_output=True, timeout=10)
    started = False
    deadline = clock() + 90
    try:
        for attempt in range(40):
            try:
                result = call('readerMeaningStart', json.dumps(payload)); started = True; break
            except subprocess.CalledProcessError:
                if attempt == 39: raise
                sleep(0.15)
        while result.get('busy'):
            if clock() >= deadline: return {'error': 'The explanation timed out. Try again.'}
            sleep(0.3)
            result = call('readerMeaningStatus', token)
        return result
    finally:
        if started:
            try: call('readerMeaningCancel', token)
            except (subprocess.SubprocessError, ValueError): pass


def main():
    def stop(signum, frame):
        raise InterruptedError('Lookup cancelled.')
    signal.signal(signal.SIGTERM, stop)
    try:
        payload = json.loads(sys.stdin.readline(12000))
        result = lookup(payload)
    except (ValueError, AttributeError, subprocess.SubprocessError, OSError) as error:
        result = {'error': 'Could not complete the assistant lookup. Check the assistant connection.'}
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
