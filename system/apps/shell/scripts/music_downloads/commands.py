#!/usr/bin/python3
import os
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlparse


BASE = Path(__file__).resolve().parent
PYTHON = Path.home() / ".local/share/venvs/zotify/bin/python"
SPOTDL = Path.home() / ".local/share/venvs/spotdl/bin/spotdl"
SETTINGS = Path.home() / ".config/zotify-gui/settings.json"


def find_spotdl():
    # Prefer the app environment: its resolver enforces spotipyfree's spotapi<2.
    if SPOTDL.is_file() and os.access(SPOTDL, os.X_OK):
        return str(SPOTDL)
    installed = shutil.which("spotdl")
    if installed:
        return installed
    raise RuntimeError("spotDL is not installed. Install the AUR package spotdl or see the app README.")


def spotify_links(text):
    links = text.split()
    if not links:
        raise ValueError("Paste at least one Spotify link.")
    for link in links:
        url = urlparse(link)
        if url.scheme != "https" or url.netloc != "open.spotify.com" or not re.fullmatch(
                r"/(?:intl-[\w-]+/)?(?:track|album|playlist|artist|episode|show)/[A-Za-z0-9]+/?", url.path):
            raise ValueError("Use full open.spotify.com links copied with Share → Copy link.")
    return links


def build_args(mode, text, folder, fmt):
    folder = Path(folder).expanduser()
    if not folder.is_absolute():
        raise ValueError("Choose an absolute download folder.")
    args = ["--root-path", str(folder), "--root-podcast-path", str(folder),
            "--download-format", fmt, "--skip-existing", "True", "--no-splash"]
    if mode == 0:
        args += spotify_links(text)
    else:
        args += ["--liked" if mode == 1 else "--followed"]
    return args


def music_links(text):
    links = []
    for link in spotify_links(text):
        parsed = urlparse(link)
        path = re.sub(r"^/intl-[\w-]+", "", parsed.path).rstrip("/")
        if path.split("/")[1] in ("episode", "show"):
            raise ValueError("spotDL supports music links only.")
        links.append("https://open.spotify.com" + path)
    return list(dict.fromkeys(links))


def build_spotdl_args(mode, text, folder, fmt, mix_tracks=False, cookie_file="", threads=4):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    if mode != 0:
        raise ValueError("For spotDL, paste a Spotify playlist, album, artist or track link.")
    if not Path(folder).expanduser().is_absolute():
        raise ValueError("Choose an absolute download folder.")
    if fmt not in ("ogg", "mp3", "flac", "wav"):
        raise ValueError("Choose a supported audio format.")
    if type(threads) is not int or threads not in (1, 2, 4):
        raise ValueError("Choose 1, 2 or 4 parallel tracks.")
    links = music_links(text)
    cookie_args = []
    if cookie_file:
        if not isinstance(cookie_file, str):
            raise ValueError("Choose a cookie file path.")
        cookies = Path(cookie_file).expanduser()
        if not cookies.is_absolute():
            raise ValueError("Choose an absolute cookie file path.")
        try:
            with cookies.open("rb") as source:
                header = source.readline(256).strip()
        except OSError:
            raise ValueError("Cookie file is missing or unreadable. Choose a readable Netscape cookies.txt file.") from None
        if header not in (b"# Netscape HTTP Cookie File", b"# HTTP Cookie File"):
            raise ValueError("Choose a Netscape cookies.txt export, not a browser database or JSON file.")
        cookie_args = ["--cookie-file", str(cookies)]
    return ["download", *links, *cookie_args, "--format", fmt, "--output",
            str(Path(folder).expanduser() / ("{track-id}.{output-ext}" if mix_tracks else "{artists} - {title}.{output-ext}")),
            "--threads", str(threads), "--overwrite", "skip", "--simple-tui", "--max-retries", "2"]




def remember_playlist_source(folder, text):
    """Keep source identity beside downloads, including folders with named files."""
    links = music_links(text)
    if len(links) != 1:
        return
    parsed = urlparse(links[0])
    match = re.fullmatch(r"/(?:intl-[\w-]+/)?playlist/([A-Za-z0-9]{22})/?", parsed.path)
    if parsed.netloc != 'open.spotify.com' or not match:
        return
    path = Path(folder) / '.enclosure-playlist.json'
    try:
        sources = json.loads(path.read_text()).get('sources', [])
    except (OSError, ValueError):
        sources = []
    uri = 'spotify:playlist:' + match[1]
    if uri not in sources:
        sources.append(uri)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(dict(sources=sources)))
    temporary.replace(path)


def publish_playlist(folder, result):
    """Publish membership only after a successful job; never delete audio."""
    songs = json.loads(Path(result).read_text())
    if not isinstance(songs, list) or any(not isinstance(s, dict) or
            not re.fullmatch(r'[A-Za-z0-9]{22}', s.get('song_id', '')) for s in songs):
        raise ValueError('Invalid Spotify playlist result; previous membership retained')
    path = Path(folder) / '.enclosure-playlist.json'
    metadata = json.loads(path.read_text())
    metadata['tracks'] = [dict(uri='spotify:track:' + s['song_id'],
        title=s.get('name', ''), artist=s.get('artist', '')) for s in songs]
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(metadata))
    temporary.replace(path)
