"""Generate timestamped English captions locally, ahead of the current position."""
import hashlib
import json
import math
import os
import re
from pathlib import Path
import struct
import subprocess
import threading
import time
import wave
from gi.repository import GLib

DATA = Path.home() / '.local/share/anime-streamer'
BINARY = DATA / 'vendor/whisper.cpp-1.9.5/build/bin/whisper-cli'
MODEL = DATA / 'models/ggml-base.en.bin'
VAD_BINARY = BINARY.with_name('whisper-vad-speech-segments')
VAD_MODEL = DATA / 'models/ggml-silero-v6.2.0.bin'
CHUNK = 16
LOOKAHEAD = 40


def srt_time(seconds):
    millis = max(0, round(seconds * 1000))
    hours, millis = divmod(millis, 3600000)
    minutes, millis = divmod(millis, 60000)
    seconds, millis = divmod(millis, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'


def cues_from_whisper(data, offset):
    words = []
    for segment in data.get('transcription', []):
        for token in segment.get('tokens', []):
            text = token.get('text', '')
            times = token.get('offsets', {})
            start, end = times.get('from', -1), times.get('to', -1)
            if not text or text.startswith(('[_', '<|')):
                continue
            if not any(char.isalnum() for char in text):
                if words:
                    words[-1][2] += text.strip()
                continue
            if start < 0:
                start = round((words[-1][1] - offset) * 1000) if words else segment.get('offsets', {}).get('from', 0)
            end = max(start + 10, end)
            if not words or text[0].isspace():
                words.append([offset + start / 1000, offset + end / 1000, text.strip()])
            else:
                words[-1][1] = offset + end / 1000
                words[-1][2] += text
    if words:
        groups, group = [], []
        for word in words:
            if group and (len(' '.join(item[2] for item in group) + ' ' + word[2]) > 42
                          or word[1] - group[0][0] > 3
                          or word[0] - group[-1][1] > .55):
                groups.append(group)
                group = []
            group.append(word)
            if word[2].endswith(('.', '?', '!', ',')) and len(group) >= 3:
                groups.append(group)
                group = []
        if group:
            groups.append(group)
        cues = []
        for index, group in enumerate(groups):
            start = group[0][0]
            end = max(start + .6, group[-1][1] + .12)
            if index + 1 < len(groups) and groups[index + 1][0][0] > start:
                end = min(end, groups[index + 1][0][0])
            cues.append((start, end, ' '.join(word[2] for word in group)))
        return cues
    cues = []
    for segment in data.get('transcription', []):
        text = segment.get('text', '').strip()
        times = segment.get('offsets', {})
        start = offset + times.get('from', 0) / 1000
        end = offset + times.get('to', 0) / 1000
        if text and end > start:
            cues.append((start, end, text))
    return cues


def write_srt(path, cues):
    output = ''.join(f'{i}\n{srt_time(start)} --> {srt_time(end)}\n{text}\n\n'
                     for i, (start, end, text) in enumerate(sorted(cues), 1))
    temp = path.with_suffix('.tmp')
    temp.write_text(output)
    temp.replace(path)


def recognize(wav, output, run=subprocess.run):
    # Keep speech spans on the original timeline. Whisper's built-in VAD
    # reports token times on compressed audio, which loses silent gaps.
    result = run([str(VAD_BINARY), '-np', '-vm', str(VAD_MODEL), '-f', str(wav),
                  '-vsd', '400', '-vp', '120', '-vmsd', '8'], timeout=20, capture_output=True)
    if result.returncode:
        raise RuntimeError('Local speech detection failed')
    spans = [(float(start) / 100, float(end) / 100)
             for start, end in re.findall(r'Speech segment \d+: start = ([\d.]+), end = ([\d.]+)', result.stdout.decode())]
    transcription = []
    with wave.open(str(wav), 'rb') as source:
        params = source.getparams()
        for index, (start, end) in enumerate(spans):
            clip = output.parent / f'{output.name}-speech-{index}.wav'
            prefix = output.parent / f'{output.name}-speech-{index}'
            try:
                source.setpos(min(source.getnframes(), round(start * params.framerate)))
                pcm = source.readframes(max(0, round((end - start) * params.framerate)))
                if not pcm:
                    continue
                with wave.open(str(clip), 'wb') as destination:
                    destination.setparams(params)
                    destination.writeframes(pcm)
                command = [str(BINARY), '-m', str(MODEL), '-f', str(clip), '-l', 'en',
                           '-t', str(min(6, os.cpu_count() or 2)), '-bs', '1', '-bo', '1',
                           '-ng', '-sns', '-np', '-ml', '64', '-sow', '-ojf', '-of', str(prefix)]
                result = run(command, timeout=90, capture_output=True)
                if result.returncode:
                    raise RuntimeError('Local speech recognition failed')
                data = json.loads(prefix.with_suffix('.json').read_text())
                for segment in data.get('transcription', []):
                    for item in [segment] + segment.get('tokens', []):
                        if 'offsets' in item:
                            item['offsets'] = {key: value + round(start * 1000) for key, value in item['offsets'].items()}
                    transcription.append(segment)
            finally:
                clip.unlink(missing_ok=True)
                prefix.with_suffix('.json').unlink(missing_ok=True)
    data = {'transcription': transcription}
    output.with_suffix('.json').write_text(json.dumps(data))
    return data


class LiveSubtitles:
    def __init__(self, links, cache, on_ready, on_status, delay=0):
        if not all(path.is_file() for path in (BINARY, MODEL, VAD_BINARY, VAD_MODEL)):
            raise RuntimeError('Local English subtitle model is not installed')
        self.source = links[3] or links[0]
        self.is_hls = getattr(links, 'is_hls', '.m3u8' in self.source.split('?', 1)[0].lower())
        self.audio_map = getattr(links, 'audio_map', '0:a:0')
        self.referer = links[1]
        self.on_ready = on_ready
        self.on_status = on_status
        digest = hashlib.sha256(self.source.encode()).hexdigest()[:24]
        self.folder = Path(cache) / 'live-subtitles' / digest / str(time.time_ns())
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / 'Live English · local Whisper.srt'
        self.condition = threading.Condition()
        self.cancelled = False
        self.process = None
        self.position = 0
        self.duration = 0
        self.blocks = {}
        self.delay = float(delay)
        self.attempts = {}
        self.started = time.monotonic()
        threading.Thread(target=self.work, daemon=True).start()

    def post(self, callback, value):
        def deliver():
            if not self.cancelled:
                callback(value)
            return False
        GLib.idle_add(deliver)

    def update_position(self, position, duration=0):
        with self.condition:
            self.position = max(0, position)
            self.duration = max(0, duration)
            self.condition.notify()

    def close(self):
        with self.condition:
            self.cancelled = True
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
            self.condition.notify_all()

    def set_delay(self, seconds):
        with self.condition:
            if self.delay == seconds:
                return
            self.delay = seconds
            self.publish()

    def publish(self):
        with self.condition:
            cues = [(max(0, start + self.delay), end + self.delay, text)
                    for batch in self.blocks.values() for start, end, text in batch
                    if end + self.delay > 0]
            if cues:
                write_srt(self.path, cues)
                self.post(self.on_ready, str(self.path))
                self.post(self.on_status, 'Local English captions ready')
            else:
                self.post(self.on_status, 'Listening for English speech…')

    def run(self, args, timeout, capture_output=False):
        with self.condition:
            if self.cancelled:
                raise InterruptedError()
            self.process = subprocess.Popen(args, stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL, stderr=subprocess.PIPE)
            process = self.process
        try:
            output, error = process.communicate(timeout=timeout)
            if process.returncode:
                if self.cancelled:
                    raise InterruptedError()
                raise RuntimeError('Audio processing failed; retrying shortly')
            return subprocess.CompletedProcess(args, process.returncode, output, error)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise RuntimeError('Local subtitle processing timed out')
        finally:
            with self.condition:
                if self.process is process:
                    self.process = None

    def transcribe(self, block):
        start = block * CHUNK
        wav = self.folder / f'chunk-{block}.wav'
        output = self.folder / f'chunk-{block}'
        args = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y']
        if self.source.startswith(('http://', 'https://')):
            # This provider uses signed HLS segments with non-media suffixes.
            # They are the same segments already decoded by the player.
            args += ['-rw_timeout', '15000000']
            if self.is_hls:
                args += ['-allowed_extensions', 'ALL', '-allowed_segment_extensions', 'ALL', '-extension_picky', '0']
            if self.referer:
                args += ['-referer', self.referer]
        args += ['-ss', str(start), '-i', self.source, '-t', str(CHUNK),
                 '-map', self.audio_map, '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(wav)]
        try:
            self.run(args, 40)
            with wave.open(str(wav), 'rb') as audio:
                pcm = audio.readframes(audio.getnframes())
            if len(pcm) < 3200:
                return []
            samples = struct.unpack('<' + 'h' * (len(pcm) // 2), pcm)
            rms = math.sqrt(sum(value * value for value in samples) / len(samples))
            if rms < 45:
                return []
            data = recognize(wav, output, run=self.run)
            return cues_from_whisper(data, start)
        finally:
            wav.unlink(missing_ok=True)
            output.with_suffix('.json').unlink(missing_ok=True)

    def work(self):
        self.post(self.on_status, 'Preparing local English captions…')
        while not self.cancelled:
            with self.condition:
                first = int(self.position // CHUNK)
                last = int((self.position + LOOKAHEAD) // CHUNK)
                if self.duration > 0:
                    last = min(last, int(max(0, self.duration - .01) // CHUNK))
                missing = [block for block in range(first, last + 1) if block not in self.blocks
                           and time.monotonic() - self.attempts.get(block, 0) > 15]
                if not missing:
                    self.condition.wait(timeout=1)
                    continue
                block = missing[0]
            try:
                cues = self.transcribe(block)
                with self.condition:
                    self.blocks[block] = cues
                    self.publish()
            except InterruptedError:
                return
            except Exception as error:
                self.attempts[block] = time.monotonic()
                self.post(self.on_status, 'Captions: ' + str(error))
