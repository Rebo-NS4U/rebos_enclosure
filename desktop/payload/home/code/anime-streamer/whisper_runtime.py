#!/usr/bin/python3
"""Compatibility entrypoint for a locally verified accelerated Whisper build."""
import math
import os
from pathlib import Path
import sys
import wave

DATA = Path.home() / '.local/share/anime-streamer/vendor/whisper.cpp-1.9.5'


def command(arguments, root=DATA):
    args = list(arguments)
    gpu = root / 'build-vulkan/bin/whisper-cli'
    if gpu.is_file() and os.access(gpu, os.X_OK):
        binary = gpu
        args = [arg for arg in args if arg not in ('-ng', '--no-gpu')]
    else:
        binary = root / 'build/bin/whisper-cli-cpu'
    # Each detected speech span is short. Avoid encoding 30 seconds of padding
    # for every phrase; retain one second of context plus a minimum 5.12s window.
    if '-ac' not in args and '--audio-ctx' not in args:
        for flag in ('-f', '--file'):
            if flag in args and args.index(flag) + 1 < len(args):
                try:
                    with wave.open(args[args.index(flag) + 1], 'rb') as audio:
                        seconds = audio.getnframes() / audio.getframerate()
                    context = min(1500, max(256, math.ceil((seconds + 1) * 50 / 64) * 64))
                    args += ['-ac', str(context)]
                except (OSError, wave.Error, EOFError):
                    pass
                break
    return [str(binary), *args]


def main():
    args = command(sys.argv[1:])
    os.execv(args[0], args)


if __name__ == '__main__':
    main()
