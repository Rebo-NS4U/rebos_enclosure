"""JSON-lines download controller for Enclosure Music."""
import json
import os
import signal
import subprocess
import sys
import threading
from commands import build_spotdl_args, find_spotdl

lock = threading.Lock()
CANCEL_GRACE = 2


def emit(**data):
    with lock:
        print(json.dumps(data), flush=True)


class Download:
    def __init__(self, command):
        self.cancelled = threading.Event()
        self.finished = threading.Event()
        self.child = subprocess.Popen(command, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True,
            env={**os.environ, 'PYTHONUNBUFFERED': '1'})

    def signal_group(self, sig):
        try:
            os.killpg(self.child.pid, sig)
        except ProcessLookupError:
            pass

    def watch(self):
        try:
            for line in self.child.stdout:
                emit(log=line.rstrip())
            code = self.child.wait()
        finally:
            if self.cancelled.is_set():
                self.signal_group(signal.SIGKILL)
            self.child.stdout.close()
            self.finished.set()
        emit(done=True, code=code, cancelled=self.cancelled.is_set())

    def cancel(self):
        if self.finished.is_set() or self.cancelled.is_set():
            return
        self.cancelled.set()
        self.signal_group(signal.SIGTERM)
        # Some downloaders swallow SIGTERM; ffmpeg or a resolver may also keep
        # stdout open after the parent exits. Bound cancellation for the group.
        def force_stop():
            if not self.finished.wait(CANCEL_GRACE):
                self.signal_group(signal.SIGKILL)
        threading.Thread(target=force_stop, daemon=True).start()


job = None
try:
    for line in sys.stdin:
        try:
            data = json.loads(line)
            if data.get('cancel'):
                if job:
                    job.cancel()
                continue
            if job and not job.finished.is_set():
                raise ValueError('A download is already running.')
            mode = int(data.get('mode', 0))
            folder = os.path.expanduser(data.get('folder') or '~/Music')
            fmt = data.get('format', 'ogg')
            if data.get('backend', 'spotdl') != 'spotdl':
                raise ValueError('Only spotDL is supported.')
            command = [find_spotdl(), *build_spotdl_args(mode, data.get('links', ''), folder, fmt, mix_tracks=data.get('mixTracks') is True)]
            os.makedirs(folder, exist_ok=True)
            job = Download(command)
            emit(started=True)
            threading.Thread(target=job.watch, daemon=True).start()
        except Exception as error:
            emit(error=str(error), busy=bool(job and not job.finished.is_set()))
finally:
    if job:
        job.cancel()
        job.finished.wait(CANCEL_GRACE + 2)
