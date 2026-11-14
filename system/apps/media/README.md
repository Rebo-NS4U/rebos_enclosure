# Rebos Streamer

Enclosure’s Quickshell media browser for anime, movies, TV and YouTube. Source, dependencies, launchers and updates are maintained in `system/apps/media` within the Enclosure repository. The UI runs in its own process; a systemd user service owns playback so closing the UI does not stop a video.

## Run

Requires Linux with a Wayland session, Quickshell (including its QtQuick Controls, Effects and Wayland modules), Python 3 with PyGObject and GTK 3 introspection, systemd user services, Node.js, mpv, VLC, yt-dlp, ffmpeg, curl, openssl and the JetBrains Mono and Phosphor icon fonts. Niri supplies focus and geometry for the next-episode overlay; other compositors are not yet validated.

Enclosure installs the app, desktop entry and playback service. Open **Rebos Streamer** from the application launcher, press **Mod+Shift+A**, or run `anime-streamer`. Development installations link `~/code/anime-streamer` to this directory; Enclosure updates keep that link and the app current. Do not install the old separate `Rebos_Streamer` checkout over these managed launchers.

The UI runs separately from the panel; the service adopts updated Python code on its next start. Updating never restarts active playback.

Primewire verification additionally uses Playwright and Chromium:

```sh
npm install --prefix ~/.local/share/anime-streamer/browser playwright
~/.local/share/anime-streamer/browser/node_modules/.bin/playwright install chromium
```

Live transcription is optional and requires the existing Whisper/model setup. Accounts, progress, settings and caches remain in the existing `anime-streamer` user data directories; none are bundled. TorBox credentials and YouTube browser accounts are connected through Settings.

A single left click on the VLC video toggles pause/play when `vlc-pause-click-plugin` is installed. Double-click still toggles fullscreen. Enclosure’s optional media group installs this plugin; standalone installations need to install it separately. Streamer enables the plugin automatically when VLC reports it available.

## Development

`ui/shell.qml` is the standalone UI entry point. `ui/modules` contains the current Enclosure/Dweebo controls, surfaces, shadows and theme defaults needed by this app; it does not import the installed shell. `vendor/ani-cli` preserves Enclosure's resolver version. `backend_server.py` and `menu_client.py` communicate over the existing per-user runtime socket.

Each backend client has a bounded output queue and a two-second write deadline;
a stalled UI disconnects without blocking playback or another UI. Requests and
events are limited to 1 MiB, with at most 16 clients and 16 queued events per
client. The byte relay retains at most 32,768 routes. Active and paused players
own complete source families, including rewritten playlist children; in-flight
requests, recently read sources and fresh preloads also protect their families.
Only inactive families are retired, together with their error and preload state.
Playlist routes are admitted together: capacity exhaustion rejects a new manifest
without emitting partially evicted links or interrupting existing owned routes.
An evicted cached source is resolved again before playback. Relay paths use
random tokens. Extremely large manifests and indefinitely growing live streams
can reach the cap and fail explicitly; sliding-window live-stream retirement is
not implemented.

Settings changes are serialized as patches, with pending feedback until the
service acknowledges persistence. Rejected changes revert to the service's
confirmed values while newer queued edits are retained. A disconnect discards
unconfirmed local edits; reconnecting reloads the service's saved values. Settings
controls are disabled offline.

Startup refuses regular files, symlinks, foreign-owned sockets and live listeners
at the runtime socket path. Only a confirmed stale socket owned by the current
user is removed; shutdown also checks that the original socket still occupies
the path.
MovieBox adapter provenance and its upstream MIT notice are retained under
`vendor/moviebox-tui/`.

```sh
cd ../../..
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=system/apps/media python3 -m unittest discover -s desktop/tests/media
```

Derived QML is covered by the included AGPL-3.0 license inherited from Enclosure's shell. Preserve upstream notices when modifying bundled sources.

The menu follows the shell wallpaper palette at `~/.cache/rebos_shell/colors.json` and watches for color changes. Built-in colors are used only when a palette role is unavailable.

The content sheet uses the opaque surface variant to keep catalogue and settings
text readable over other windows. This does not rewrite shell transparency or
theme preferences. Playback checkboxes and sliders follow the shared colors and
keyboard focus styling. Hover a catalogue card, or select it with the keyboard,
to read its full title; Play tooltips also include the title.

Streamer also watches Enclosure’s `rebos_shell/config/theme.json` under the XDG config directory. OLED backgrounds, surface style, transparency, fonts and other theme preferences update live. Missing settings use portable defaults; Streamer never writes shell preferences. Light mode disables OLED, matching the shell.
