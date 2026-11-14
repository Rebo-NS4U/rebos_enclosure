#!/usr/bin/env bash
# Reuse the existing player so opening the library preserves its queue/playback.
set -eu
music_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if quickshell ipc -p "$music_root/Music.qml" call music open 2>/dev/null; then
    exit 0
fi
# Qt's native PipeWire output is killed on playback on affected Qt builds.
# Use PipeWire's PulseAudio compatibility server; keep explicit user overrides.
export QT_AUDIO_BACKEND="${QT_AUDIO_BACKEND:-pulseaudio}"
exec quickshell -n -p "$music_root/Music.qml"
