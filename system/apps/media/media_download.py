"""Save one resolved video as a local file."""
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from gi.repository import GLib

import media_sources
import stream_relay

DOWNLOAD_TIMEOUT = 6 * 60 * 60
HLS_OPTIONS = ['-allowed_extensions', 'ALL', '-allowed_segment_extensions', 'ALL',
               '-extension_picky', '0', '-seg_max_retry', '3']


def save(title, transfer):
    directory = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
    folder = Path(directory or Path.home() / 'Downloads') / 'Rebos Streamer'
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title).strip(' .')
    stem = name.encode()[:180].decode(errors='ignore') or 'Video'
    folder.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.download-', dir=folder) as temporary:
        video = Path(temporary) / 'video.mkv'
        transfer(video)
        if not video.is_file() or not video.stat().st_size:
            raise ValueError('The source did not produce a video file.')
        number = 1
        while True:
            suffix = '' if number == 1 else f' ({number})'
            target = folder / f'{stem}{suffix}.mkv'
            try:
                os.link(video, target)
            except FileExistsError:
                number += 1
            else:
                return str(target)


def download_youtube(episode, quality, output):
    url = media_sources.youtube_url(episode)
    template = str(output.with_suffix('')).replace('%', '%%') + '.%(ext)s'
    media_sources.ytdlp([
        '--no-playlist', '--match-filters', '!is_live', '--no-progress',
        '-S', 'res,fps,vcodec:h264,acodec:aac', '-f', media_sources.youtube_format(quality),
        '--merge-output-format', 'mkv', '--remux-video', 'mkv',
        '-o', template,
        '--', url,
    ], timeout=DOWNLOAD_TIMEOUT)


def relay_input(url, referer):
    if url.startswith('https://'):
        return stream_relay.register(url, {'Referer': referer} if referer else {})
    return url


def input_options(url, hls):
    return ['-rw_timeout', '15000000', '-protocol_whitelist', 'http,https,tcp,tls,crypto,data',
            *(HLS_OPTIONS if hls else []), '-i', url]


def download_stream(links, kind, output):
    video, referer, _, audio = links
    video = relay_input(video, referer)
    audio = relay_input(audio, referer)
    hls = kind == 'anime' or getattr(links, 'is_hls', False)
    args = ['ffmpeg', '-nostdin', '-loglevel', 'error', '-xerror', *input_options(video, hls)]
    audio_map = getattr(links, 'audio_map', '0:a:0?')
    if audio:
        args.extend(input_options(audio, hls))
        audio_map = '1:a:0'
    args.extend(['-map', '0:v:0', '-map', audio_map, '-c', 'copy', str(output)])
    owner = object()
    try:
        with stream_relay.playback(owner, [url for url in (video, audio) if url]):
            result = subprocess.run(args, capture_output=True, timeout=DOWNLOAD_TIMEOUT)
            if result.returncode:
                raise ValueError('Could not save the video. Try again or choose another quality.')
    except subprocess.TimeoutExpired:
        raise ValueError('The download timed out.') from None
    finally:
        stream_relay.release(owner)
