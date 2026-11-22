#!/usr/bin/env python3
"""Install Anime Streamer's local caption engine and models (no service restart)."""
import os
import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

DATA = Path.home() / '.local/share/anime-streamer'
VERSION = '1.9.5'
SOURCE_SHA256 = 'ff1a9053feb509ff9d7729703355541ae9690073a6b1c40eb692c962e0dc1720'
MODEL_REVISION = '5359861c739e955e79d9a303bcbc70fb988958b1'
VAD_REVISION = '9ffd54a1e1ee413ddf265af9913beaf518d1639b'
MODEL_SHA256 = {
    'small.en-q5_1': 'bfdff4894dcb76bbf647d56263ea2a96645423f1669176f4844a1bf8e478ad30',
    'base.en': 'a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002',
    'base': '60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe',
    'medium-q5_0': '19fea4b380c3a618ec4723c3eef2eb785ffba0d0538cf43f8f235e7b3b34220f',
}
VAD_SHA256 = '2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987'


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(url, path, digest):
    if path.is_file() and checksum(path) == digest:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f'Downloading {path.name}', flush=True)
    descriptor, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    partial = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            with urllib.request.urlopen(url, timeout=60) as response:
                while block := response.read(1024 * 1024):
                    stream.write(block)
        if checksum(partial) != digest:
            raise RuntimeError('Subtitle download checksum mismatch: ' + path.name)
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)


def main():
    for tool in ('cmake', 'c++', 'ffmpeg'):
        if not shutil.which(tool):
            raise SystemExit(f'Install {tool} before running this setup.')
    source = DATA / f'vendor/whisper.cpp-{VERSION}'
    if not (source / 'CMakeLists.txt').is_file():
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'whisper.tar.gz'
            download(f'https://codeload.github.com/ggml-org/whisper.cpp/tar.gz/refs/tags/v{VERSION}', archive, SOURCE_SHA256)
            source.parent.mkdir(parents=True, exist_ok=True)
            with tarfile.open(archive) as bundle:
                bundle.extractall(source.parent, filter='data')
    subprocess.run(['cmake', '-S', str(source), '-B', str(source / 'build'),
                    '-DCMAKE_BUILD_TYPE=Release', '-DWHISPER_BUILD_TESTS=OFF',
                    '-DWHISPER_BUILD_SERVER=OFF', '-DGGML_CUDA=OFF'], check=True)
    subprocess.run(['cmake', '--build', str(source / 'build'), '--parallel',
                    str(min(4, os.cpu_count() or 2)), '--target',
                    'whisper-cli', 'whisper-vad-speech-segments'], check=True)
    for model, digest in MODEL_SHA256.items():
        download(f'https://huggingface.co/ggerganov/whisper.cpp/resolve/{MODEL_REVISION}/ggml-{model}.bin',
                 DATA / f'models/ggml-{model}.bin', digest)
    download(f'https://huggingface.co/ggml-org/whisper-vad/resolve/{VAD_REVISION}/ggml-silero-v6.2.0.bin',
             DATA / 'models/ggml-silero-v6.2.0.bin', VAD_SHA256)
    print('Local subtitle engine installed. Toggle captions off/on to retry an existing playback.')


if __name__ == '__main__':
    main()
