#!/usr/bin/env bash
# Finish downloads from a regular terminal with network access.
set -euo pipefail
INSTALL_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$INSTALL_DIR/.." && pwd)

for dependency in curl python3 tar; do
    command -v "$dependency" >/dev/null || { printf 'Missing dependency: %s\n' "$dependency" >&2; exit 1; }
done
if [[ ! -x "$HOME/.local/bin/zen" ]]; then
    curl -fsSL https://github.com/zen-browser/updates-server/raw/refs/heads/main/install.sh | bash
fi
install -Dm755 "$REPO_DIR/.local/bin/zen-browser" "$HOME/.local/bin/zen-browser"
if [[ ! -f "$HOME/.zen/profiles.ini" ]]; then
    "$HOME/.local/bin/zen" -CreateProfile rebos_shell
fi
# Route launcher entries through the same wrapper as the Niri shortcut.
python3 - <<'PY'
from pathlib import Path
home = Path.home()
p = home / '.local/share/applications/zen.desktop'
if p.exists():
    text = p.read_text().replace(str(home / '.tarball-installations/zen/zen'), str(home / '.local/bin/zen-browser'))
    p.write_text(text)
PY
python3 "$REPO_DIR/.config/quickshell/scripts/apply_app_palette.py"

if ! command -v spotify >/dev/null && ! command -v spotify-launcher >/dev/null; then
    if command -v paru >/dev/null; then
        paru -S --needed spotify-launcher
    else
        printf 'Install Spotify, then rerun this script to enable its theme.\n' >&2
        exit 1
    fi
fi
if ! command -v spicetify >/dev/null && [[ ! -x "$HOME/.spicetify/spicetify" ]]; then
    curl -fsSL https://raw.githubusercontent.com/spicetify/cli/main/install.sh | sh
fi
if [[ ! -f "$HOME/.config/spotify/prefs" ]]; then
    printf 'Zen is installed and themed. Open Spotify and sign in once, then rerun this script.\n'
    if command -v spotify-launcher >/dev/null; then
        spotify-launcher >/dev/null 2>&1 &
    else
        spotify >/dev/null 2>&1 &
    fi
    exit 0
fi
SPICE_BIN=$(command -v spicetify || printf '%s' "$HOME/.spicetify/spicetify")
# Initialize its configuration before setting owned theme keys.
"$SPICE_BIN" config current_theme rebos_shell color_scheme rebos_shell inject_css 1 replace_colors 1
SPOTIFY_DIR="$HOME/.local/share/spotify-launcher/install/usr/share/spotify"
if [[ -d "$SPOTIFY_DIR" ]]; then
    "$SPICE_BIN" config spotify_path "$SPOTIFY_DIR"
fi
"$SPICE_BIN" config prefs_path "$HOME/.config/spotify/prefs"
python3 "$REPO_DIR/.config/quickshell/scripts/apply_app_palette.py"
"$SPICE_BIN" backup apply
printf 'Zen, Spotify and VS Code share the QuickShell palette. Restart Zen after palette changes.\n'
