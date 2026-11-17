"""JSON-lines download controller for Enclosure Music."""
import json
import os
import signal
import subprocess
import sys
import threading
from commands import build_spotdl_args, find_spotdl

proc = None
lock = threading.Lock()
def emit(**data):
    with lock:
        print(json.dumps(data), flush=True)
def watch(child):
    for line in child.stdout:
        emit(log=line.rstrip())
    emit(done=True, code=child.wait())
def cancel():
    if proc and proc.poll() is None:
        try: os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError: pass
try:
    for line in sys.stdin:
        try:
            data = json.loads(line)
            if data.get('cancel'):
                cancel()
                continue
            if proc and proc.poll() is None:
                raise ValueError('A download is already running.')
            mode = int(data.get('mode', 0))
            folder = os.path.expanduser(data.get('folder') or '~/Music')
            fmt = data.get('format', 'ogg')
            if data.get('backend', 'spotdl') != 'spotdl':
                raise ValueError('Only spotDL is supported.')
            command = [find_spotdl(), *build_spotdl_args(mode, data.get('links', ''), folder, fmt, mix_tracks=data.get('mixTracks') is True)]
            os.makedirs(folder, exist_ok=True)
            proc = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'})
            emit(started=True)
            threading.Thread(target=watch, args=(proc,), daemon=True).start()
        except Exception as error:
            emit(error=str(error))
finally:
    cancel()
