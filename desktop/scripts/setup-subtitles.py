#!/usr/bin/env python3
"""Install Anime Streamer's local caption engine and models (no service restart)."""
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

DATA = Path.home() / '.local/share/anime-streamer'
VERSION = '1.9.5'


def download(url, path):
    if path.is_file() and path.stat().st_size:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + '.part')
    print(f'Downloading {path.name}', flush=True)
    urllib.request.urlretrieve(url, partial)
    partial.replace(path)


def main():
    for tool in ('cmake', 'c++', 'ffmpeg'):
        if not shutil.which(tool):
            raise SystemExit(f'Install {tool} before running this setup.')
    source = DATA / f'vendor/whisper.cpp-{VERSION}'
    if not (source / 'CMakeLists.txt').is_file():
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'whisper.tar.gz'
            download(f'https://codeload.github.com/ggml-org/whisper.cpp/tar.gz/refs/tags/v{VERSION}', archive)
            source.parent.mkdir(parents=True, exist_ok=True)
            with tarfile.open(archive) as bundle:
                bundle.extractall(source.parent, filter='data')
    subprocess.run(['cmake', '-S', str(source), '-B', str(source / 'build'),
                    '-DCMAKE_BUILD_TYPE=Release', '-DWHISPER_BUILD_TESTS=OFF',
                    '-DWHISPER_BUILD_SERVER=OFF', '-DGGML_CUDA=OFF'], check=True)
    subprocess.run(['cmake', '--build', str(source / 'build'), '--parallel',
                    str(min(4, os.cpu_count() or 2)), '--target',
                    'whisper-cli', 'whisper-vad-speech-segments'], check=True)
    for model in ('base.en', 'base'):
        download(f'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{model}.bin',
                 DATA / f'models/ggml-{model}.bin')
    download('https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin',
             DATA / 'models/ggml-silero-v6.2.0.bin')
    print('Local subtitle engine installed. Toggle captions off/on to retry an existing playback.')


if __name__ == '__main__':
    main()
