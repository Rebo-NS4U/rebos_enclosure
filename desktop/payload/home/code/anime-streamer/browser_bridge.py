"""Launch only the app-owned verification browser, with private JSON transport."""
import json
from pathlib import Path
import subprocess
import threading

_LOCK = threading.Lock()
_CURRENT = None


def cancel():
    global _CURRENT
    with _LOCK:
        process = _CURRENT
    if process is not None and process.poll() is None:
        process.terminate()


def resolve(url, expected):
    global _CURRENT
    helper = Path(__file__).with_name('primewire_browser.cjs')
    with _LOCK:
        if _CURRENT is not None and _CURRENT.poll() is None:
            raise RuntimeError('Finish or close the current Primewire verification first.')
        process = subprocess.Popen(['node', str(helper)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        _CURRENT = process
    try:
        try:
            output, _ = process.communicate(json.dumps(dict(url=url, expected=expected)) + '\n', timeout=210)
        except subprocess.TimeoutExpired:
            process.terminate()
            try: process.communicate(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.communicate()
            raise RuntimeError('Primewire verification timed out. Complete its check and start a video when retrying.') from None
        try:
            data = json.loads(output.strip().splitlines()[-1])
        except (ValueError, IndexError):
            raise RuntimeError('Primewire verification was closed before a video was selected.') from None
        if not data.get('ok'):
            raise RuntimeError(data.get('error') or 'Primewire verification failed.')
        return data['stream']
    finally:
        with _LOCK:
            if _CURRENT is process:
                _CURRENT = None
