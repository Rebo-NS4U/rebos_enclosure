#!/usr/bin/env python3
"""Offline reader speech; network access happens only with --setup."""
import argparse
import base64
import json
import math
from dataclasses import dataclass
import queue
import threading
import time
import hashlib
import re
import urllib.request
import os
from pathlib import Path
import signal
import subprocess
import sys
import venv
import tempfile

VOICE = 'af_heart'
PROFILES = {
    'kokoro-heart': ('af_heart', 'Heart'),
    'kokoro-bella': ('af_bella', 'Bella'),
    'kokoro-michael': ('am_michael', 'Michael'),
    'kokoro-fenrir': ('am_fenrir', 'Fenrir'),
}
KOKORO = 'kokoro-onnx==0.4.7'
KOKORO_ASSETS = {
    'kokoro-v1.0.onnx': '7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5',
    'voices-v1.0.bin': 'bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d',
}



def data_dir():
    override = os.environ.get('ENCLOSURE_READER_SPEECH_DIR')
    if override:
        return Path(override)
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'enclosure/reader-speech'


def ready(directory, profile="kokoro-heart"):
    return (directory / 'venv/bin/python').is_file() and all(
        (directory / 'kokoro' / name).is_file() for name in KOKORO_ASSETS)


def download_model(target, digest):
    def checksum(path):
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    if target.is_file() and checksum(target) == digest:
        return
    temporary = target.with_suffix(target.suffix + '.part')
    # Runtime 0.4.7 needs the original tokens/float-speed model export.
    release = 'model-files-v1.0' if target.name == 'kokoro-v1.0.onnx' else 'model-files-v1.1'
    url = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/' + release + '/' + target.name
    try:
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open('wb') as stream:
            while block := response.read(1024 * 1024):
                stream.write(block)
        if checksum(temporary) != digest:
            raise RuntimeError('Voice download checksum mismatch. Try setup again.')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def setup(directory, profile="kokoro-heart"):
    directory.mkdir(parents=True, exist_ok=True)
    environment = directory / 'venv'
    if not (environment / 'bin/python').exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    python = str(environment / 'bin/python')
    subprocess.run([python, '-m', 'pip', 'install', KOKORO], check=True)
    models = directory / 'kokoro'
    models.mkdir(exist_ok=True)
    for name, digest in KOKORO_ASSETS.items():
        download_model(models / name, digest)


class PlaybackControl:
    """Ordered stdin controls pause the player and freeze the highlight clock."""
    def __init__(self):
        self.lock = threading.RLock()
        self.player = None
        self.paused_at = None
        self.paused_total = 0.0

    def set_paused(self, paused):
        with self.lock:
            if paused == (self.paused_at is not None): return
            now = time.monotonic()
            if paused: self.paused_at = now
            else:
                self.paused_total += now - self.paused_at
                self.paused_at = None
            if self.player is not None and self.player.poll() is None:
                try: self.player.send_signal(signal.SIGSTOP if paused else signal.SIGCONT)
                except ProcessLookupError: pass

    def attach(self, player):
        with self.lock:
            self.player = player
            if self.paused_at is not None: player.send_signal(signal.SIGSTOP)

    def now(self):
        with self.lock:
            return (self.paused_at if self.paused_at is not None else time.monotonic()) - self.paused_total

    def wait_until(self, deadline, cancelled):
        while not cancelled.is_set():
            with self.lock:
                remaining = deadline - self.now()
                if self.paused_at is None and remaining <= 0: return True
            if cancelled.wait(min(0.025, max(0.005, remaining))): break
        return False

    def read_commands(self):
        def apply(command):
            if command.strip() == 'pause': self.set_paused(True)
            elif command.strip() == 'resume': self.set_paused(False)
        try:
            fd = sys.stdin.fileno()
        except (AttributeError, OSError, ValueError):
            for command in sys.stdin: apply(command)
            return
        # Avoid a daemon thread holding Python's buffered stdin lock at exit.
        pending = b''
        try:
            while block := os.read(fd, 4096):
                pending += block
                while b'\n' in pending:
                    command, pending = pending.split(b'\n', 1)
                    apply(command.decode('ascii', errors='ignore'))
        except OSError:
            return



@dataclass
class TimedAudio:
    data: bytes
    cues: list


def word_cues(text, duration, offset=0):
    """Estimate UTF-16 word boundaries within actual synthesized audio duration."""
    words = list(re.finditer(r'\S+', text))
    weights = [max(1, len(re.sub(r'\W', '', word.group()))) ** 0.65 for word in words]
    total = sum(weights)
    elapsed = 0.0
    cues = []
    for word, weight in zip(words, weights):
        start = len(text[:word.start()].encode('utf-16-le')) // 2 + offset
        end = len(text[:word.end()].encode('utf-16-le')) // 2 + offset
        cues.append((elapsed, start, end))
        elapsed += duration * weight / total
    cues.append((duration, -1, -1))
    return cues


def narration_chunk_end(text, begin, end, limit):
    """Prefer sentence boundaries, then whitespace, for a bounded speech chunk."""
    stop = end
    sentence_boundary = False
    if end - begin > limit:
        window = text[begin:begin + limit]
        candidates = []
        for match in re.finditer(r'[.!?]["\'”’)]*(?=\s)', window):
            prefix = window[:match.end()].rstrip('"\'”’)')
            if re.search(r'(?:\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|etc)|\b[A-Z])\.$', prefix):
                continue
            if match.end() >= limit // 3:
                candidates.append(match.end())
        if candidates:
            stop = begin + candidates[-1]
            sentence_boundary = True
        else:
            space = window.rfind(' ')
            stop = begin + (space if space > 0 else limit)
    return stop, sentence_boundary


def narration_units(text, paragraphs=None, limit=180):
    """Keep punctuation/context together; split only paragraphs or bounded chunks."""
    utf16 = [0]
    for char in text:
        utf16.append(utf16[-1] + len(char.encode('utf-16-le')) // 2)
    positions = {offset: index for index, offset in enumerate(utf16)}
    boundaries = {0, len(text)}
    for offset in paragraphs or []:
        if offset in positions:
            boundaries.add(positions[offset])
    boundaries.update(match.end() for match in re.finditer(r'\n\s*\n|\u2029', text))
    boundaries = sorted(boundaries)
    units = []
    for begin, end in zip(boundaries, boundaries[1:]):
        while begin < end and text[begin].isspace():
            begin += 1
        end = len(text[:end].rstrip())
        while begin < end:
            stop, sentence_boundary = narration_chunk_end(text, begin, end, limit)
            units.append((begin, text[begin:stop], 0.18 if sentence_boundary else 0.04))
            begin = stop
            while begin < end and text[begin].isspace():
                begin += 1
        if units:
            start, body, _ = units[-1]
            units[-1] = (start, body, 0.12)
    if units:
        start, body, _ = units[-1]
        units[-1] = (start, body, 0.0)
    return units


def cached_page(text, profile, speed, paragraphs):
    """A bounded, private runtime cache; no book text or durable audio library."""
    base = Path(os.environ.get('XDG_RUNTIME_DIR', tempfile.gettempdir())) / ('enclosure-reader-' + str(os.getuid()))
    base.mkdir(mode=0o700, exist_ok=True)
    if base.is_symlink() or base.stat().st_uid != os.getuid() or base.stat().st_mode & 0o077:
        raise RuntimeError('Reader audio cache must be private.')
    key = json.dumps([2, text, profile, speed, paragraphs or []], ensure_ascii=True)
    return base / (hashlib.sha256(key.encode()).hexdigest() + '.json')


def read_cached_page(path):
    try:
        if time.time() - path.stat().st_mtime > 3600:
            path.unlink(missing_ok=True)
            return None
        return [TimedAudio(base64.b64decode(item['audio']), item['cues'])
                for item in json.loads(path.read_text())]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def store_cached_page(path, chunks):
    payload = [{'audio': base64.b64encode(chunk.data if isinstance(chunk, TimedAudio) else chunk).decode('ascii'),
                'cues': chunk.cues if isinstance(chunk, TimedAudio) else []} for chunk in chunks]
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream)
        temporary.replace(path)
        # At most three ready pages, including concurrent reader views.
        for old in sorted(path.parent.glob('*.json'), key=lambda item: item.stat().st_mtime, reverse=True)[3:]:
            old.unlink(missing_ok=True)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def kokoro_chunks(text, directory, profile, speed, paragraphs):
    import numpy as np
    from kokoro_onnx import Kokoro
    models = directory / 'kokoro'
    voice = Kokoro(str(models / 'kokoro-v1.0.onnx'), str(models / 'voices-v1.0.bin'))
    # Multiple sentences share one model call for natural punctuation and
    # abbreviations. Explicit silence is only for actual chunk/paragraph joins.
    for start, sentence, pause in narration_units(text, paragraphs):
        # Soft line wraps must not become pauses in the model's input. Keeping
        # one character per whitespace preserves the source word-cue offsets.
        samples, rate = voice.create(re.sub(r'\s', ' ', sentence), voice=PROFILES[profile][0], speed=speed, lang='en-us')
        if rate != 24000:
            raise RuntimeError('Unexpected Kokoro sample rate.')
        audio = (np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes()
        yield TimedAudio(audio, word_cues(sentence, len(audio) / (2 * rate),
                                         len(text[:start].encode('utf-16-le')) // 2))
        if pause:
            yield bytes(round(rate * pause / speed) * 2)


def buffered_start(chunks, rate, seconds=6.0, max_chunks=12):
    """Prepare a speech reserve before a short heading can start playback.

    The rest stays streaming: a bounded queue prepares several chunks ahead
    while PipeWire plays, rather than using a paragraph pause as a queue slot.
    """
    chunks = iter(chunks)
    initial = []
    duration = 0.0
    for chunk in chunks:
        initial.append(chunk)
        data = chunk.data if isinstance(chunk, TimedAudio) else chunk
        duration += len(data) / (2 * rate)
        if duration >= seconds or len(initial) >= max_chunks:
            break
    yield from initial
    yield from chunks


@dataclass(frozen=True)
class RenderOptions:
    speed: float = 1.05
    paragraphs: list | None = None
    control: PlaybackControl | None = None
    prepare: bool = False


def render_kokoro(text, directory, output=None, profile="kokoro-heart", options=None):
    options = options or RenderOptions()
    cache = cached_page(text, profile, options.speed, options.paragraphs) if options.prepare or output is None else None
    cached = read_cached_page(cache) if cache is not None else None
    if cached is not None:
        if not options.prepare: return play_audio(cached, 24000, output, options.control)
        return
    if options.prepare:
        store_cached_page(cache, kokoro_chunks(text, directory, profile, options.speed, options.paragraphs))
    else:
        chunks = kokoro_chunks(text, directory, profile, options.speed, options.paragraphs)
        return play_audio(chunks if output else buffered_start(chunks, 24000), 24000, output, options.control)


def write_audio_file(chunks, rate, output):
    import wave
    with wave.open(str(output), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        for chunk in chunks:
            wav.writeframes(chunk.data if isinstance(chunk, TimedAudio) else chunk)


def stream_audio(stream, timeline, control, player, rate):
    buffered, finished = stream
    audio_end = 0.0
    while True:
        chunk = buffered.get()
        if chunk is finished:
            break
        if isinstance(chunk, Exception):
            raise chunk
        data = chunk.data if isinstance(chunk, TimedAudio) else chunk
        # Account for synthesis gaps, the pipe's backpressure, and the
        # player's 100 ms buffer instead of timing from process startup.
        origin = max(audio_end, control.now() + 0.1)
        if isinstance(chunk, TimedAudio):
            timeline.put((origin, chunk.cues))
        audio_end = origin + len(data) / (2 * rate)
        player.stdin.write(data)
        player.stdin.flush()


def emit_audio_words(timeline, control, cancelled):
    while not cancelled.is_set():
        try:
            item = timeline.get(timeout=0.1)
        except queue.Empty:
            continue
        origin, cues = item
        for at, start, end in cues:
            if not control.wait_until(origin + at, cancelled):
                return
            print(json.dumps({'start': start, 'end': end}), flush=True)


def stop_audio_player(player, control):
    if player is not None and player.poll() is None:
        control.set_paused(False)
        player.terminate()
        try:
            player.wait(timeout=2)
        except subprocess.TimeoutExpired:
            player.kill()
            player.wait()


def play_audio(chunks, rate, output=None, control=None):
    control = control or PlaybackControl()
    if output:
        write_audio_file(chunks, rate, output)
        return
    player = None
    cancelled = threading.Event()
    buffered = queue.Queue(maxsize=6)
    finished = object()
    def produce_audio():
        try:
            for chunk in chunks:
                while not cancelled.is_set():
                    try:
                        buffered.put(chunk, timeout=0.1)
                        break
                    except queue.Full:
                        pass
                if cancelled.is_set():
                    return
        except Exception as error:
            enqueue(error)
        finally:
            enqueue(finished)
    def enqueue(item):
        while not cancelled.is_set():
            try:
                buffered.put(item, timeout=0.1)
                return
            except queue.Full:
                pass
    producer = threading.Thread(target=produce_audio, daemon=True)
    timeline = queue.Queue()
    clock = threading.Thread(target=emit_audio_words, args=(timeline, control, cancelled), daemon=True)
    clock.start()
    previous = signal.getsignal(signal.SIGTERM)
    def cancel(signum, frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, cancel)
    try:
        producer.start()
        player = subprocess.Popen(['pw-play', '--raw', '--rate', str(rate),
                                   '--channels', '1', '--format', 's16',
                                   '--media-role', 'Accessibility', '-'], stdin=subprocess.PIPE)
        control.attach(player)
        stream_audio((buffered, finished), timeline, control, player, rate)
        player.stdin.close()
        if player.wait() != 0:
            raise RuntimeError('Audio playback failed. Check the audio output.')
    finally:
        cancelled.set()
        stop_audio_player(player, control)
        clock.join(timeout=0.5)
        if producer.is_alive(): producer.join(timeout=0.5)
        signal.signal(signal.SIGTERM, previous)


def speaking_speed(value):
    speed = float(value)
    if not math.isfinite(speed) or not 0.5 <= speed <= 2.0:
        raise argparse.ArgumentTypeError('Speed must be between 0.5 and 2.0.')
    return speed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=tuple(PROFILES), default='kokoro-heart')
    parser.add_argument('--paragraphs', type=json.loads, default=[])
    parser.add_argument('--speed', type=speaking_speed, default=1.05)
    parser.add_argument('--setup', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--prepare', action='store_true', help='Preload a page without playing it')
    parser.add_argument('--wav', type=Path, help='Render a WAV instead of playing audio')
    parser.add_argument('text', nargs='?', default='')
    args = parser.parse_args()
    directory = data_dir()
    if args.status:
        print(json.dumps({'kokoro': ready(directory), 'voice': VOICE, 'voices': [{'id': key, 'title': item[1]} for key, item in PROFILES.items()]}))
    elif args.setup:
        setup(directory, args.profile)
    elif args.text.strip():
        if args.worker:
            control = PlaybackControl()
            if args.prepare:
                def cancel_preparation(signum, frame):
                    raise SystemExit(0)
                signal.signal(signal.SIGTERM, cancel_preparation)
            if not args.wav and not args.prepare:
                threading.Thread(target=control.read_commands, daemon=True).start()
                print(json.dumps({'ready': True}), flush=True)
            render_kokoro(args.text, directory, args.wav, args.profile,
                          RenderOptions(args.speed, args.paragraphs, control, args.prepare))
            if args.prepare: print(json.dumps({'prepared': True}), flush=True)
        elif ready(directory, args.profile):
            # Replace the launcher so Stop targets the actual synthesis process.
            command = [str(directory / 'venv/bin/python'), '-B', str(Path(__file__).resolve()), '--profile', args.profile, '--speed', str(args.speed), '--paragraphs', json.dumps(args.paragraphs), '--worker']
            if args.wav:
                command += ['--wav', str(args.wav)]
            if args.prepare: command += ['--prepare']
            os.execv(command[0], command + ['--', args.text])
        else:
            raise RuntimeError('Download voices from Reader settings before using Read aloud.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
