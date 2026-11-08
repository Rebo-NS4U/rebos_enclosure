#!/usr/bin/env python3
"""Offline reader speech; network access happens only with --setup."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import venv

VOICE = 'en_US-lessac-high'
PIPER = 'piper-tts==1.8.0'


def data_dir():
    override = os.environ.get('ENCLOSURE_READER_SPEECH_DIR')
    if override:
        return Path(override)
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'enclosure/reader-speech'


def ready(directory):
    return all(path.is_file() for path in (
        directory / 'venv/bin/python',
        directory / 'voices' / (VOICE + '.onnx'),
        directory / 'voices' / (VOICE + '.onnx.json')))


def setup(directory):
    directory.mkdir(parents=True, exist_ok=True)
    environment = directory / 'venv'
    if not (environment / 'bin/python').exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    python = str(environment / 'bin/python')
    subprocess.run([python, '-m', 'pip', 'install', PIPER], check=True)
    voices = directory / 'voices'
    voices.mkdir(exist_ok=True)
    subprocess.run([python, '-m', 'piper.download_voices', '--download-dir', str(voices), VOICE], check=True)


def render(text, directory, output=None):
    from piper import PiperVoice
    voice = PiperVoice.load(str(directory / 'voices' / (VOICE + '.onnx')))
    if output:
        import wave
        with wave.open(str(output), 'wb') as wav:
            voice.synthesize_wav(text, wav)
        return
    player = None
    previous = signal.getsignal(signal.SIGTERM)
    def cancel(signum, frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, cancel)
    try:
        player = subprocess.Popen(['pw-play', '--raw', '--rate', str(voice.config.sample_rate),
                                   '--channels', '1', '--format', 's16',
                                   '--media-role', 'Accessibility', '-'], stdin=subprocess.PIPE)
        for chunk in voice.synthesize(text):
            player.stdin.write(chunk.audio_int16_bytes)
            player.stdin.flush()
        player.stdin.close()
        if player.wait() != 0:
            raise RuntimeError('Audio playback failed. Check the audio output.')
    finally:
        if player is not None and player.poll() is None:
            player.terminate()
            try:
                player.wait(timeout=2)
            except subprocess.TimeoutExpired:
                player.kill()
                player.wait()
        signal.signal(signal.SIGTERM, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--wav', type=Path, help='Render a WAV instead of playing audio')
    parser.add_argument('text', nargs='?', default='')
    args = parser.parse_args()
    directory = data_dir()
    if args.status:
        print(json.dumps({'natural': ready(directory), 'voice': VOICE}))
    elif args.setup:
        setup(directory)
    elif args.text.strip():
        if args.worker:
            render(args.text, directory, args.wav)
        elif ready(directory):
            # Replace the launcher so Stop targets the actual synthesis process.
            command = [str(directory / 'venv/bin/python'), '-B', str(Path(__file__).resolve()), '--worker']
            if args.wav:
                command += ['--wav', str(args.wav)]
            os.execv(command[0], command + ['--', args.text])
        elif args.wav:
            raise RuntimeError('Set up the natural voice before rendering a WAV.')
        else:
            os.execvp('espeak-ng', ['espeak-ng', '-s', '165', '--', args.text])


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
