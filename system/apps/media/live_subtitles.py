"""Generate timestamped English captions locally, ahead of the current position."""
from dataclasses import dataclass
import hashlib
from itertools import groupby
import json
import math
import os
import re
from pathlib import Path
import struct
import subprocess
import textwrap
import threading
import time
import wave
from gi.repository import GLib

DATA = Path.home() / '.local/share/anime-streamer'
BINARY = DATA / 'vendor/whisper.cpp-1.9.5/build/bin/whisper-cli'
MODEL = DATA / 'models/ggml-base.en.bin'
MULTILINGUAL_MODEL = DATA / 'models/ggml-base.bin'
FRENCH_GERMAN_MODEL = DATA / 'models/ggml-medium-q5_0.bin'
TRANSLATION_LANGUAGES = {'es': 'Spanish', 'fr': 'French', 'de': 'German'}
CAPTION_LANGUAGES = ('en', 'auto', *TRANSLATION_LANGUAGES)
VAD_BINARY = BINARY.with_name('whisper-vad-speech-segments')
VAD_MODEL = DATA / 'models/ggml-silero-v6.2.0.bin'
CHUNK = 8
LOOKAHEAD = 40
LINE_WIDTH = 42
MAX_CUE_SECONDS = 6
SPEECH_BREAK = 1.0


def srt_time(seconds):
    millis = max(0, round(seconds * 1000))
    hours, millis = divmod(millis, 3600000)
    minutes, millis = divmod(millis, 60000)
    seconds, millis = divmod(millis, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'


def whisper_words(segments, offset):
    words = []
    for segment in segments:
        segment_start = len(words)
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
            if len(words) == segment_start or text[0].isspace():
                words.append([offset + start / 1000, offset + end / 1000, text.strip()])
            else:
                words[-1][1] = offset + end / 1000
                words[-1][2] += text
    return words


def ends_sentence(word):
    word = word.rstrip("”’\"')]}")
    if word.casefold() in {'mr.', 'mrs.', 'ms.', 'dr.', 'prof.', 'e.g.', 'i.e.'}:
        return False
    if re.fullmatch(r'(?:[A-Z]\.)+', word):
        return False
    return word.endswith(('.', '?', '!', '…'))


def wrapped_lines(words):
    return textwrap.wrap(' '.join(words), width=LINE_WIDTH, break_long_words=False,
                         break_on_hyphens=False)


def caption_lines(words):
    words = list(words)
    lines = wrapped_lines(words)
    if len(lines) != 2:
        return lines
    # Prefer a clause boundary, then the most balanced pair of lines.
    candidates = [(' '.join(words[:i]), ' '.join(words[i:])) for i in range(1, len(words))]
    fitting = [pair for pair in candidates if max(map(len, pair)) <= LINE_WIDTH]
    return min(fitting, key=lambda pair: (not pair[0].endswith((',', ';', ':', '—')),
                                          abs(len(pair[0]) - len(pair[1]))), default=lines)


def timed_groups(words):
    group = []
    for word in words:
        if group and (ends_sentence(group[-1][2]) or word[0] - group[-1][1] >= SPEECH_BREAK):
            yield group
            group = []
        group.append(word)
        while len(group) > 1 and (group[-1][1] - group[0][0] > MAX_CUE_SECONDS or
                                  len(wrapped_lines(item[2] for item in group)) > 2):
            # When a sentence needs multiple cues, keep clauses together.
            cut = next((i for i in range(len(group) - 1, 0, -1)
                        if group[i - 1][2].endswith((',', ';', ':', '—'))), len(group) - 1)
            yield group[:cut]
            group = group[cut:]
    if group:
        yield group


def translated_lines(text):
    # Only the whole translated span has reliable timing. Put its sentences
    # on separate lines within that span, preserving the speech boundaries.
    lines, sentence = [], []
    for word in text.split():
        sentence.append(word)
        if ends_sentence(word):
            lines.extend(caption_lines(sentence))
            sentence = []
    return '\n'.join(lines + caption_lines(sentence))


def timed_cues(words):
    groups = list(timed_groups(words))
    cues = []
    for index, group in enumerate(groups):
        start = group[0][0]
        end = max(start + .6, group[-1][1] + .12)
        if index + 1 < len(groups) and groups[index + 1][0][0] > start:
            end = min(end, groups[index + 1][0][0])
        cues.append((start, end, '\n'.join(caption_lines(word[2] for word in group))))
    return cues


def segment_cues(segments, offset):
    cues = []
    for segment in segments:
        text = segment.get('text', '').strip()
        times = segment.get('offsets', {})
        start = offset + times.get('from', 0) / 1000
        end = offset + times.get('to', 0) / 1000
        if text and end > start:
            cues.append((start, end, translated_lines(text)))
    return cues


def cues_from_whisper(data, offset):
    cues = []
    # Adjacent word-timed segments can form one sentence in mixed-language audio.
    for timed, batch in groupby(data.get('transcription', []), key=lambda s: bool(s.get('tokens'))):
        segments = list(batch)
        words = whisper_words(segments, offset) if timed else []
        cues.extend(timed_cues(words) if words else segment_cues(segments, offset))
    return cues


def write_srt(path, cues):
    output = ''.join(f'{i}\n{srt_time(start)} --> {srt_time(end)}\n{text}\n\n'
                     for i, (start, end, text) in enumerate(sorted(cues), 1))
    temp = path.with_suffix('.tmp')
    temp.write_text(output)
    temp.replace(path)


def speech_spans(output, language):
    spans = [(float(start) / 100, float(end) / 100)
             for start, end in re.findall(r'Speech segment \d+: start = ([\d.]+), end = ([\d.]+)', output.decode())]
    if language != 'en':
        return spans
    # Decode nearby English phrases together with the intervening audio
    # intact. Translation and auto detection still need per-span anchors.
    phrases = []
    for start, end in spans:
        if phrases and start - phrases[-1][1] <= 1:
            phrases[-1] = (phrases[-1][0], end)
        else:
            phrases.append((start, end))
    return phrases


def caption_model(language):
    if language == 'en':
        return MODEL
    if language in ('fr', 'de') and FRENCH_GERMAN_MODEL.is_file():
        return FRENCH_GERMAN_MODEL
    return MULTILINGUAL_MODEL


def decoding_options(model, duration):
    if model == FRENCH_GERMAN_MODEL:
        # Whisper uses 50 audio context tokens per second. Leave room for
        # padding beyond the speech, within the model's 30-second window.
        context = min(1500, max(384, round(duration * 50) + 100))
        return ['-bs', '5', '-bo', '5', '-ac', str(context), '-oj']
    return ['-bs', '1', '-bo', '1', '-sns', '-ml', '64', '-sow', '-ojf']


# Quality exception: Speech-span boundaries, language selection, timestamps and cleanup are explicit within one bounded recognition operation.
# Numeric ceilings are enforced by desktop/scripts/quality.py.
def recognize(wav, output, run=subprocess.run, language='en', on_progress=None):  # pylint: disable=too-many-branches,too-many-locals
    if language not in CAPTION_LANGUAGES:
        raise ValueError('Unsupported caption language')
    model = caption_model(language)
    # Keep speech spans on the original timeline. Whisper's built-in VAD
    # reports token times on compressed audio, which loses silent gaps.
    result = run([str(VAD_BINARY), '-np', '-vm', str(VAD_MODEL), '-f', str(wav),
                  '-vsd', '400', '-vp', '120', '-vmsd', '8'], timeout=20, capture_output=True)
    if result.returncode:
        raise RuntimeError('Local speech detection failed')
    spans = speech_spans(result.stdout, language)
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
                command = [str(BINARY), '-m', str(model), '-f', str(clip), '-l', language,
                           '-t', str(min(6, os.cpu_count() or 2)), '-ng', '-np', '-of', str(prefix)]
                command += decoding_options(model, len(pcm) / (params.sampwidth * params.nchannels * params.framerate))
                if language != 'en':
                    command += ['--translate']
                result = run(command, timeout=90, capture_output=True)
                if result.returncode:
                    raise RuntimeError('Local speech recognition failed')
                data = json.loads(prefix.with_suffix('.json').read_text())
                if language in TRANSLATION_LANGUAGES or (language == 'auto' and data.get('result', {}).get('language') != 'en'):
                    # Translation reorders words. Anchor each translated phrase to
                    # its original speech span instead of English token times.
                    text = ' '.join(segment.get('text', '').strip()
                                    for segment in data.get('transcription', [])).strip()
                    if text:
                        transcription.append({'text': text, 'offsets': {
                            'from': round(start * 1000), 'to': round(end * 1000)}})
                    if on_progress:
                        on_progress({'transcription': list(transcription)})
                    continue
                for segment in data.get('transcription', []):
                    for item in [segment] + segment.get('tokens', []):
                        if 'offsets' in item:
                            item['offsets'] = {key: value + round(start * 1000) for key, value in item['offsets'].items()}
                    transcription.append(segment)
                if on_progress:
                    on_progress({'transcription': list(transcription)})
            finally:
                clip.unlink(missing_ok=True)
                prefix.with_suffix('.json').unlink(missing_ok=True)
    data = {'transcription': transcription}
    output.with_suffix('.json').write_text(json.dumps(data))
    return data


@dataclass(frozen=True)
class CaptionOptions:
    delay: float = 0
    language: str = 'en'
    position: float = 0
    duration: float = 0


# Quality exception: One owner controls this process/session lifetime; explicit state fields preserve existing transition invariants.
# Numeric ceilings are enforced by desktop/scripts/quality.py.
class LiveSubtitles:  # pylint: disable=too-many-instance-attributes
    def __init__(self, links, cache, on_ready, on_status, *, options=None):
        options = options or CaptionOptions()
        delay, language = options.delay, options.language
        position, duration = options.position, options.duration
        if language not in CAPTION_LANGUAGES:
            raise ValueError('Unsupported caption language')
        self.language = language
        model = caption_model(language)
        if not all(path.is_file() for path in (BINARY, model, VAD_BINARY, VAD_MODEL)):
            raise RuntimeError(f'Local subtitle model is not installed: {model.name}')
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
        self.position = max(0, position)
        self.duration = max(0, duration)
        self.blocks = {}
        self.partial = {}
        self.last_status = None
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
            self.publish_status()
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

    def publish_status(self):
        first = int(max(0, self.position - self.delay) // CHUNK)
        if first in self.blocks:
            mode = TRANSLATION_LANGUAGES.get(self.language, 'Auto language')
            text = ('Local English captions ready' if self.language == 'en'
                    else f'{mode} → English captions ready')
            if not self.blocks[first]:
                text = 'No speech detected in the current scene'
        else:
            text = 'Generating captions for the current scene…'
        if text != self.last_status:
            self.last_status = text
            self.post(self.on_status, text)

    def publish(self):
        with self.condition:
            cues = [(max(0, start + self.delay), end + self.delay, text)
                    for batch in (self.blocks | self.partial).values() for start, end, text in batch
                    if end + self.delay > 0]
            if cues:
                write_srt(self.path, cues)
                self.post(self.on_ready, str(self.path))
            self.publish_status()

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
            def progress(data):
                with self.condition:
                    self.partial[block] = cues_from_whisper(data, start)
                    self.publish()
            data = recognize(wav, output, run=self.run, language=self.language, on_progress=progress)
            return cues_from_whisper(data, start)
        finally:
            wav.unlink(missing_ok=True)
            output.with_suffix('.json').unlink(missing_ok=True)

    def work(self):
        mode = {'auto': 'automatic English', 'en': 'local English'}.get(self.language)
        if mode is None:
            mode = f'{TRANSLATION_LANGUAGES[self.language]} → English'
        self.post(self.on_status, f'Preparing {mode} captions…')
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
                # Fill the nearest missing chunk first. Jumping to a moving
                # lookahead deadline leaves holes in otherwise ready captions.
                block = missing[0]
            try:
                cues = self.transcribe(block)
                with self.condition:
                    self.blocks[block] = cues
                    if cues != self.partial.pop(block, []):
                        self.publish()
                    else:
                        self.publish_status()
            except InterruptedError:
                return
            except Exception as error:
                self.attempts[block] = time.monotonic()
                self.post(self.on_status, 'Captions: ' + str(error))
