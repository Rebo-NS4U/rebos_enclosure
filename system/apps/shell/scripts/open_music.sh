#!/usr/bin/env bash
# Reuse the existing player so opening the library preserves its queue/playback.
set -eu
music_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# Reuse Spotify without raising it or changing active playback.
if ! gdbus call --session --dest org.freedesktop.DBus \
    --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.NameHasOwner \
    org.mpris.MediaPlayer2.spotify 2>/dev/null | grep -q true; then
    if command -v spotify-launcher >/dev/null 2>&1; then
        gtk-launch spotify-launcher >/dev/null 2>&1 &
    elif command -v spotify >/dev/null 2>&1; then
        spotify >/dev/null 2>&1 &
    elif command -v flatpak >/dev/null 2>&1 && flatpak info com.spotify.Client >/dev/null 2>&1; then
        flatpak run com.spotify.Client >/dev/null 2>&1 &
    fi
fi
if quickshell ipc -p "$music_root/Music.qml" call music open 2>/dev/null; then
    exit 0
fi
# Qt's native PipeWire output is killed on playback on affected Qt builds.
# Use PipeWire's PulseAudio compatibility server; keep explicit user overrides.
export QT_AUDIO_BACKEND="${QT_AUDIO_BACKEND:-pulseaudio}"
exec quickshell -n -p "$music_root/Music.qml"
