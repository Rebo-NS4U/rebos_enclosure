#!/usr/bin/env bash
# Reuse the existing player so opening the library preserves its queue/playback.
set -eu
music_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if quickshell ipc -p "$music_root/Music.qml" call music open 2>/dev/null; then
    exit 0
fi
exec quickshell -n -p "$music_root/Music.qml"
