#!/usr/bin/env python3
"""Stream spectrum levels from the default audio output monitor; never the mic.

Only numeric levels go to stdout. Audio is neither stored nor sent over a network.
"""
import array
import cmath
import json
import math
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


def main():
    def stop(*_):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    child = None
    try:
        child = subprocess.Popen(['parec', '--device=@DEFAULT_MONITOR@', '--raw',
            '--format=s16le', '--rate=' + str(RATE), '--channels=1', '--latency-msec=40'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        while True:
            raw = child.stdout.read(SIZE * 2)
            if len(raw) != SIZE * 2:
                break
            samples = array.array('h', raw)
            if sys.byteorder != 'little':
                samples.byteswap()
            print(json.dumps(spectrum(samples)), flush=True)
    except (OSError, BrokenPipeError):
        pass
    finally:
        if child is not None:
            child.terminate()
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    main()
