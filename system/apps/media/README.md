# Rebos Streamer

Standalone Quickshell media browser for anime, movies, TV and YouTube, extracted from Rebos Enclosure. The UI runs in its own process; a systemd user service owns playback so closing the UI does not stop a video.

## Run

Requires Linux with a Wayland session, Quickshell (including its QtQuick Controls, Effects and Wayland modules), Python 3 with PyGObject and GTK 3 introspection, systemd user services, Node.js, mpv, VLC, yt-dlp, ffmpeg, curl, openssl and the JetBrains Mono and Phosphor icon fonts. Niri supplies focus and geometry for the next-episode overlay; other compositors are not yet validated.

```sh
python3 install.py
./launch
```

The installer writes only user launchers, a desktop entry and `anime-streamer.service`, then reloads systemd definitions. Keep this checkout in place. It never restarts active playback. A previously running service adopts the new code on its next start.

Primewire verification additionally uses Playwright and Chromium:

```sh
npm install --prefix ~/.local/share/anime-streamer/browser playwright
~/.local/share/anime-streamer/browser/node_modules/.bin/playwright install chromium
```

Live transcription is optional and requires the existing Whisper/model setup. Accounts, progress, settings and caches remain in the existing `anime-streamer` user data directories; none are bundled. TorBox credentials and YouTube browser accounts are connected through Settings.

## Development

`ui/shell.qml` is the standalone UI entry point. `ui/modules` contains the Dweebo visual components and defaults needed by this app; it does not import the installed shell. `vendor/ani-cli` preserves Enclosure's resolver version. `backend_server.py` and `menu_client.py` communicate over the existing per-user runtime socket.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m unittest discover -s tests
```

Derived QML is covered by the included AGPL-3.0 license inherited from Enclosure's shell. Preserve upstream notices when modifying bundled sources.
