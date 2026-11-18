---
name: desktop-work
description: Desktop changes, live troubleshooting, and privileged desktop actions.
---

Desktop access: Empty ps/pgrep results in a restricted command session do not prove desktop apps are stopped. Check the user service and session connection (systemctl --user, D-Bus, WAYLAND_DISPLAY, XDG_RUNTIME_DIR and NIRI_SOCKET) using available tools. If access is restricted, request the tool's supported approval for the specific desktop check or action and retry after approval; never bypass isolation or a denied approval. If approval is unavailable, state that exact limitation. Never claim a restart succeeded without checking it. Quickshell QML and Niri configuration hot-reload automatically; do not kill or restart them for config edits. Anime Streamer mpv launch changes apply on the next playback launch; they do not require restarting VLC or Quickshell. Preserve active playback and assistant backends unless the user requests a restart.

Local desktop context: Assistant source: ~/code/rebos-assistant; shell config: ~/.config/quickshell. Inspect and edit these files for requested panel changes. Establish access with tools. If blocked, request the tool's supported approval; report unavailable or rejected approval and the exact blocked action. Never bypass sandbox or approval. Use ~/.local/bin/assistant-sudo --reason 'reason' -- command for each administrator action. Preserve unrelated work and active backends.
