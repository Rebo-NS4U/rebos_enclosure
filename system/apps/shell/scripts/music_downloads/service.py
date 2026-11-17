"""JSON-lines download controller for Enclosure Music."""
import json
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path
from commands import build_spotdl_args, find_spotdl

lock = threading.Lock()
CANCEL_GRACE = 2


def emit(**data):
    with lock:
        print(json.dumps(data), flush=True)


class Download:
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


class WarmDownload(Download):
    """Use a preloaded parent, keeping each job in a separate process group."""
    def __init__(self, worker, command):
        self.worker = worker
        self.pid = None
        self.cancelled = threading.Event()
        self.finished = threading.Event()
        worker.stdin.write(json.dumps(command) + '\n')
        worker.stdin.flush()

    def signal_group(self, sig):
        if self.pid is not None:
            try:
                os.killpg(self.pid, sig)
            except ProcessLookupError:
                # The child may not have called setsid yet. SIGTERM defaults to
                # termination in the forked child, so signal it directly too.
                try:
                    os.kill(self.pid, sig)
                except ProcessLookupError:
                    pass

    def watch(self):
        code = 1
        try:
            for line in self.worker.stdout:
                data = json.loads(line)
                if 'pid' in data:
                    self.pid = data['pid']
                    if self.cancelled.is_set():
                        self.signal_group(signal.SIGKILL)
                elif data.get('done'):
                    code = data['code']
                    break
                else:
                    emit(**data)
        except Exception as error:
            emit(log='Download worker failed: ' + str(error))
        finally:
            if self.cancelled.is_set():
                self.signal_group(signal.SIGKILL)
            self.finished.set()
        emit(done=True, code=code, cancelled=self.cancelled.is_set())


def start_worker():
    executable = Path(find_spotdl())
    interpreter = executable.with_name('python')
    if not interpreter.is_file():
        interpreter = Path(sys.executable)
    try:
        native = 'from spotdl' in executable.read_text()[:4096]
    except (OSError, UnicodeError):
        native = False
    return subprocess.Popen([str(interpreter), '-u', str(Path(__file__).with_name('warm.py')),
        *(['--native'] if native else [])],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        env={**os.environ, 'PYTHONUNBUFFERED': '1'})


worker = None
try:
    worker = start_worker()
except (OSError, RuntimeError):
    pass  # Surface installation errors only when a download is requested.


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
            command = [find_spotdl(), *build_spotdl_args(mode, data.get('links', ''), folder, fmt, mix_tracks=data.get('mixTracks') is True, cookie_file=data.get('cookieFile', ''))]
            os.makedirs(folder, exist_ok=True)
            if worker is None or worker.poll() is not None:
                worker = start_worker()
            job = WarmDownload(worker, command)
            emit(started=True)
            threading.Thread(target=job.watch, daemon=True).start()
        except Exception as error:
            emit(error=str(error), busy=bool(job and not job.finished.is_set()))
finally:
    if job:
        job.cancel()
        job.finished.wait(CANCEL_GRACE + 2)

    if worker:
        worker.stdin.close()
        try:
            worker.wait(timeout=CANCEL_GRACE + 2)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait()
        worker.stdout.close()
