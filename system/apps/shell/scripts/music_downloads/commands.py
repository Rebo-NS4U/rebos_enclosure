#!/usr/bin/python3
import os
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


def build_args(mode, text, folder, fmt):
    folder = Path(folder).expanduser()
    if not folder.is_absolute():
        raise ValueError("Choose an absolute download folder.")
    args = ["--root-path", str(folder), "--root-podcast-path", str(folder),
            "--download-format", fmt, "--skip-existing", "True", "--no-splash"]
    if mode == 0:
        links = text.split()
        if not links:
            raise ValueError("Paste at least one Spotify link.")
        for link in links:
            url = urlparse(link)
            if url.scheme != "https" or url.netloc != "open.spotify.com" or not re.fullmatch(
                    r"/(?:intl-[\w-]+/)?(?:track|album|playlist|artist|episode|show)/[A-Za-z0-9]+/?", url.path):
                raise ValueError("Use full open.spotify.com links copied with Share → Copy link.")
        args += links
    else:
        args += ["--liked" if mode == 1 else "--followed"]
    return args


def build_spotdl_args(mode, text, folder, fmt, mix_tracks=False):
    if mode != 0:
        raise ValueError("For spotDL, paste a Spotify playlist, album, artist or track link.")
    build_args(mode, text, folder, fmt)
    if fmt not in ("ogg", "mp3", "flac", "wav"):
        raise ValueError("Choose a supported audio format.")
    links = []
    for link in text.split():
        parsed = urlparse(link)
        path = re.sub(r"^/intl-[\w-]+", "", parsed.path)
        if path.split("/")[1] in ("episode", "show"):
            raise ValueError("spotDL supports music links; use Zotify for podcasts.")
        links.append("https://open.spotify.com" + path.rstrip("/"))
    return ["download", *links, "--format", fmt, "--output",
            str(Path(folder).expanduser() / ("{track-id}.{output-ext}" if mix_tracks else "{artists} - {title}.{output-ext}")),
            "--threads", "2", "--overwrite", "skip", "--simple-tui", "--max-retries", "2"]


