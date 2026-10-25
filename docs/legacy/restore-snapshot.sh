#!/usr/bin/env bash
set -euo pipefail

dry_run=false
case "${1:-}" in
    --dry-run) dry_run=true ;;
    '') ;;
    *) printf 'Usage: %s [--dry-run]\n' "$0" >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { printf 'Too many arguments\n' >&2; exit 2; }

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
backup="$HOME/.local/state/dotfiles/backups/$(date +%Y%m%d-%H%M%S)-$$"

link_file() {
    local source=$1 relative=$2 destination="$HOME/$2"
    if [[ -L "$destination" && "$(readlink -- "$destination")" == "$source" ]]; then
        return
    fi
    printf 'Link %s -> %s\n' "$destination" "$source"
    if [[ -e "$destination" || -L "$destination" ]]; then
        printf '  Backup: %s/%s\n' "$backup" "$relative"
    fi
    if "$dry_run"; then return; fi
    mkdir -p -- "$(dirname -- "$destination")"
    if [[ -e "$destination" || -L "$destination" ]]; then
        mkdir -p -- "$backup/$(dirname -- "$relative")"
        mv -- "$destination" "$backup/$relative"
    fi
    ln -s -- "$source" "$destination"
}

shopt -s nullglob dotglob
for source in "$repo"/.config/*; do
    link_file "$source" ".config/$(basename -- "$source")"
done
for name in .bashrc .bash_profile .bash_logout; do
    link_file "$repo/$name" "$name"
done
for subtree in .local/bin .local/share/applications .local/share/fonts; do
    [[ -d "$repo/$subtree" ]] || continue
    while IFS= read -r -d '' source; do
        link_file "$source" "${source#"$repo/"}"
    done < <(find "$repo/$subtree" \( -type f -o -type l \) -print0)
done
