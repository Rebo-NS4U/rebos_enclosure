#!/usr/bin/env python3
"""Install user launchers and playback unit without restarting any service."""
from pathlib import Path
import os, shlex, subprocess, sys
root = Path(__file__).resolve().parent
home = Path.home()
def write(relative, text, executable=False):
    path = home / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if executable: path.chmod(0o755)
write('.local/bin/anime-streamer', '#!/bin/sh\nexec ' + shlex.quote(str(root / 'launch')) + ' "$@"\n', True)
def unit_quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'
write('.config/systemd/user/anime-streamer.service', '[Unit]\nDescription=Rebos Streamer playback service\nAfter=graphical-session.target\nPartOf=graphical-session.target\n[Service]\nType=simple\nExecStart=' + unit_quote(sys.executable) + ' -u ' + unit_quote(root / 'backend_server.py') + '\nRestart=on-failure\nRestartSec=2\nTimeoutStopSec=5\n')
write('.local/share/applications/rebos-shell-anime.desktop', '[Desktop Entry]\nType=Application\nName=Rebos Streamer\nComment=Anime, movies, TV and YouTube\nExec=' + str(home / '.local/bin/anime-streamer') + '\nIcon=video-x-generic\nCategories=AudioVideo;Video;\nTerminal=false\n')
subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
print('Installed user launcher and unit. Existing playback was not restarted.')
