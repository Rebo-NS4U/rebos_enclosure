#!/usr/bin/env python3
"""Stream spectrum levels from application playback, excluding system sounds.

Only numeric levels go to stdout. Audio is neither stored nor sent over a network.
"""
import array
import cmath
import json
import math
import os
import selectors
import time
import signal
import subprocess
import sys

SIZE = 1024
RATE = 24000
BANDS = 32
WINDOW = [0.5 - 0.5 * math.cos(2 * math.pi * i / (SIZE - 1)) for i in range(SIZE)]
ROOTS = {size: cmath.exp(-2j * math.pi / size) for size in (2 ** n for n in range(1, 11))}


def fft(samples):
    """Return Hann-windowed FFT values."""
    values = [complex(sample / 32768 * window) for sample, window in zip(samples, WINDOW)]
    j = 0
    for i in range(1, SIZE):
        bit = SIZE >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            values[i], values[j] = values[j], values[i]
    size = 2
    while size <= SIZE:
        half = size // 2
        for start in range(0, SIZE, size):
            factor = 1
            for offset in range(half):
                first = values[start + offset]
                second = values[start + offset + half] * factor
                values[start + offset] = first + second
                values[start + offset + half] = first - second
                factor *= ROOTS[size]
        size *= 2
    return values


def spectrum(samples):
    """Group the FFT into logarithmic bands from 50 Hz to 10 kHz."""
    values = fft(samples)
    levels = []
    for band in range(BANDS):
        low = max(1, int(50 * 200 ** (band / BANDS) * SIZE / RATE))
        high = max(low + 1, int(50 * 200 ** ((band + 1) / BANDS) * SIZE / RATE))
        peak = max(abs(value) for value in values[low:high]) * 4 / SIZE
        levels.append(round(min(1.0, peak ** 0.55), 4))
    return levels


def playback_streams():
    """Select audible app streams; event roles and shell feedback are system sounds."""
    result = subprocess.run(['pactl', '-f', 'json', 'list', 'sink-inputs'],
                            capture_output=True, text=True, timeout=2, check=True)
    sinks = subprocess.run(['pactl', '-f', 'json', 'list', 'sinks'],
                           capture_output=True, text=True, timeout=2, check=True)
    monitors = {int(s['index']): s.get('monitor_source_name', s.get('monitor_source')) for s in json.loads(sinks.stdout)}
    streams = {}
    for stream in json.loads(result.stdout):
        props = stream.get('properties', {})
        role = props.get('media.role', '').lower()
        app = props.get('application.id', '').lower()
        binary = props.get('application.process.binary', '').lower()
        # Qt Multimedia's music player shares Quickshell's app identity.
        # SoundEffect feedback does not use the QtmPulseStream media name.
        shell_music = props.get('media.name', '').startswith('QtmPulseStream-')
        shell = app == 'org.quickshell' or binary in {'quickshell', 'qs'}
        inaudible = stream.get('corked') or stream.get('mute')
        if (inaudible
                or role in {'event', 'notification', 'alert', 'system'}
                or (shell and not shell_music) or binary == 'canberra-gtk-play'):
            continue
        if int(stream['sink']) in monitors:
            streams[int(stream['index'])] = monitors[int(stream['sink'])]
    return streams


def stop_capture(selector, state):
    child = state['child']
    selector.unregister(child.stdout)
    child.terminate()
    try:
        child.wait(timeout=2)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()
    child.stdout.close()


def main():  # pylint: disable=too-many-branches
    def stop(*_):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    captures = {}
    selector = selectors.DefaultSelector()
    refresh = 0
    try:
        while True:
            now = time.monotonic()
            if now >= refresh:
                # Fail closed if the audio server cannot identify playback streams.
                try:
                    streams = playback_streams()
                except (OSError, ValueError, subprocess.SubprocessError):
                    streams = {}
                for index in list(captures):
                    state = captures[index]
                    if streams.get(index) != state['sink'] or state['child'].poll() is not None:
                        stop_capture(selector, captures.pop(index))
                for index, sink in streams.items():
                    if index in captures:
                        continue
                    child = subprocess.Popen(['parec', '--device=' + str(sink),
                        '--monitor-stream=' + str(index), '--raw', '--format=s16le',
                        '--rate=' + str(RATE), '--channels=1', '--latency-msec=40'],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    os.set_blocking(child.stdout.fileno(), False)
                    state = dict(child=child, sink=sink, buffer=b'', levels=[0] * BANDS, updated=now)
                    captures[index] = state
                    selector.register(child.stdout, selectors.EVENT_READ, state)
                refresh = now + 0.3
            for key, _ in selector.select(timeout=0.04):
                state = key.data
                raw = os.read(key.fileobj.fileno(), SIZE * 16)
                if not raw:
                    continue
                state['buffer'] += raw
                while len(state['buffer']) >= SIZE * 2:
                    samples = array.array('h', state['buffer'][:SIZE * 2])
                    state['buffer'] = state['buffer'][SIZE * 2:]
                    if sys.byteorder != 'little':
                        samples.byteswap()
                    state['levels'] = spectrum(samples)
                    state['updated'] = time.monotonic()
            active = [s['levels'] for s in captures.values()
                      if time.monotonic() - s['updated'] < 0.2]
            print(json.dumps([max((levels[i] for levels in active), default=0)
                              for i in range(BANDS)]), flush=True)
    except (OSError, BrokenPipeError):
        pass
    finally:
        for state in captures.values():
            stop_capture(selector, state)
        selector.close()


if __name__ == '__main__':
    main()
