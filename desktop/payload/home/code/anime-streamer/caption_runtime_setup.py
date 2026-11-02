#!/usr/bin/env python3
"""Build and validate acceleration before atomically updating the CLI entrypoint."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import wave

ROOT = Path.home() / '.local/share/anime-streamer/vendor/whisper.cpp-1.9.5'


def activate(root=ROOT):
    cli = root / 'build/bin/whisper-cli'
    backup = cli.with_name('whisper-cli-cpu')
    wrapper = Path(__file__).with_name('whisper_runtime.py').read_bytes()
    current = cli.read_bytes()
    if current.startswith(b'\x7fELF'):
        if backup.exists():
            if backup.read_bytes() != current:
                raise RuntimeError('CPU backup differs; refusing to replace it')
        else:
            shutil.copy2(cli, backup)
    elif current != wrapper:
        raise RuntimeError('Unknown Whisper entrypoint; refusing to replace it')
    elif not backup.exists():
        raise RuntimeError('CPU fallback is missing')
    fd, name = tempfile.mkstemp(prefix='.whisper-cli-', dir=cli.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(wrapper)
        Path(name).chmod(0o755)
        os.replace(name, cli)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample', required=True, type=Path, help='Representative speech WAV for validation')
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root
    build = root / 'build-vulkan'
    subprocess.run(['cmake', '-S', str(root), '-B', str(build), '-DCMAKE_BUILD_TYPE=Release',
                    '-DGGML_VULKAN=ON', '-DWHISPER_BUILD_TESTS=OFF', '-DWHISPER_BUILD_SERVER=OFF'], check=True)
    subprocess.run(['cmake', '--build', str(build), '--target', 'whisper-cli', '--parallel', '2'], check=True)
    from whisper_runtime import command
    model = root.parents[1] / 'models/ggml-base.bin'
    with wave.open(str(args.sample), 'rb') as audio:
        duration = audio.getnframes() / audio.getframerate()
    with tempfile.TemporaryDirectory(prefix='caption-runtime-check-') as folder:
        prefix = Path(folder) / 'result'
        invocation = command(['-m', str(model), '-f', str(args.sample), '-l', 'auto',
                              '--translate', '-t', '4', '-bs', '1', '-bo', '1', '-sns', '-np',
                              '-ojf', '-of', str(prefix)], root=root)
        started = time.monotonic()
        subprocess.run(invocation, check=True, timeout=120)
        elapsed = time.monotonic() - started
        import json
        result = json.loads(prefix.with_suffix('.json').read_text())
        if not result.get('transcription'):
            raise RuntimeError('Validation sample produced no transcript; acceleration was not activated')
        if elapsed >= duration:
            raise RuntimeError(f'Generation took {elapsed:.2f}s for {duration:.2f}s audio; acceleration was not activated')
    activate(root)
    print(f'Validated {duration:.2f}s of speech in {elapsed:.2f}s; activated for the next caption chunk. Playback was not restarted.')


if __name__ == '__main__':
    main()
