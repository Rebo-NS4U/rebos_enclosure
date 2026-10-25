#!/usr/bin/env bash
# Run after opening Zen and signing into Spotify once on the new machine.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
generator="$HOME/.config/quickshell/scripts/apply_app_palette.py"
[[ -f $generator ]] || { printf 'Install the desktop files first.\n' >&2; exit 1; }
python3 "$generator"
if command -v spicetify >/dev/null; then
    spotify_path="$HOME/.local/share/spotify-launcher/install/usr/share/spotify"
    if [[ -d $spotify_path && -f $HOME/.config/spotify/prefs ]]; then
        spicetify config spotify_path "$spotify_path" prefs_path "$HOME/.config/spotify/prefs"
        spicetify config current_theme rebos_shell color_scheme rebos_shell inject_css 1 replace_colors 1
        spicetify backup apply
    else
        printf 'Open Spotify Launcher, sign in, close it, then rerun this helper.\n'
    fi
else
    printf 'Install spicetify-cli to enable the Spotify theme.\n'
fi
printf 'Restart Zen after its profile has been themed. Wallpaper colors update through rebos_shell.\n'
