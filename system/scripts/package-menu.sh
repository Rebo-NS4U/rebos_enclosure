#!/usr/bin/env bash
# Shared package menu and backend for the Fish update command.
set -uo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ADMIN="$SCRIPT_DIR/package-admin.sh"
# Shortcuts start Bash directly, so load the same live palette used by Fish.
# fzf rereads this file for each menu/picker, including after a theme change.
theme_options="${XDG_CACHE_HOME:-$HOME/.cache}/rebos_shell/fzf.conf"
if [[ -r $theme_options ]]; then
    export FZF_DEFAULT_OPTS_FILE="$theme_options"
fi
dry_run=0
update_only=0
for argument in "$@"; do
    case $argument in
        --update) update_only=1 ;;
        --dry-run) dry_run=1 ;;
        --help|-h)
            printf 'Usage: package-menu.sh [--update [--dry-run]]\n'
            printf 'Menu: install official packages, install AUR packages, uninstall, update everything.\n'
            printf 'Updates cover Arch/AUR, system/user Flatpaks and Rust toolchains.\n'
            exit 0 ;;
        *) printf 'Unknown option: %s\n' "$argument" >&2; exit 2 ;;
    esac
done
if ((dry_run && !update_only)); then
    printf 'Use --update --dry-run to preview updates.\n' >&2
    exit 2
fi

run() {
    if ((dry_run)); then printf '%q ' "$@"; printf '\n'; else "$@"; fi
}

aur_helper() {
    if command -v paru >/dev/null; then printf 'paru\n'
    elif command -v yay >/dev/null; then printf 'yay\n'
    else return 1; fi
}

update_all() {
    local helper result=0 status
    printf '\nUpdating Arch and AUR packages\n'
    if helper=$(aur_helper); then
        run "$helper" --sudo "$ADMIN" --sudoflags '' --nosudoloop -Syu --devel
    else
        printf 'No AUR helper found; updating official repositories only.\n'
        run "$ADMIN" pacman -Syu
    fi
    status=$?
    if ((status == 130 || status == 143)); then return "$status"; fi
    if ((status != 0)); then printf 'Arch/AUR update failed.\n' >&2; result=1; fi
    if command -v flatpak >/dev/null; then
        printf '\nUpdating system Flatpaks\n'
        run "$ADMIN" flatpak update --system
        status=$?
        if ((status == 130 || status == 143)); then return "$status"; fi
        if ((status != 0)); then printf 'System Flatpak update failed.\n' >&2; result=1; fi
        printf '\nUpdating user Flatpaks\n'
        run flatpak update --user
        status=$?
        if ((status == 130 || status == 143)); then return "$status"; fi
        if ((status != 0)); then printf 'User Flatpak update failed.\n' >&2; result=1; fi
    fi
    if command -v rustup >/dev/null; then
        printf '\nUpdating Rust toolchains\n'
        run rustup update --no-self-update
        status=$?
        if ((status == 130 || status == 143)); then return "$status"; fi
        if ((status != 0)); then printf 'Rust toolchain update failed.\n' >&2; result=1; fi
    fi
    if ((result == 0)); then
        if ((dry_run)); then printf '\nPreview complete; nothing was changed.\n'
        else printf '\nAll update stages completed successfully.\n'; fi
    else
        printf '\nSome update stages failed; see the messages above.\n' >&2
    fi
    return "$result"
}

if ((update_only)); then update_all; exit $?; fi
for dependency in fzf pacman; do
    command -v "$dependency" >/dev/null || { printf 'Missing tool: %s\n' "$dependency" >&2; exit 1; }
done
work_dir=$(mktemp -d) || exit 1
trap 'rm -rf -- "$work_dir"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

select_packages() {
    local mode=$1 selection helper preview
    local -a packages picker
    case $mode in
        install)
            pacman -Slq | sort -u > "$work_dir/packages" || return 1
            preview='pacman -Si {1}' ;;
        aur)
            helper=$(aur_helper) || { printf 'Install Paru or Yay first to use the AUR.\n' >&2; return 1; }
            printf 'Loading the AUR package catalog…\n'
            curl -fLsS --retry 1 --connect-timeout 15 --max-time 120 \
                https://aur.archlinux.org/packages.gz -o "$work_dir/aur.gz" || return 1
            gzip -dc "$work_dir/aur.gz" | sed '/^#/d; /^$/d' > "$work_dir/packages" || return 1
            preview="$helper -Si {1}" ;;
        uninstall)
            pacman -Qq > "$work_dir/packages" || return 1
            preview='pacman -Qi {1}' ;;
    esac
    picker=(fzf --multi --prompt='Packages > ' --header='Tab: select multiple · Enter: continue · Esc: back'
        --preview "$preview" --preview-window 'down:60%:wrap'
        --bind 'alt-p:toggle-preview,alt-j:preview-down,alt-k:preview-up')
    selection=$("${picker[@]}" < "$work_dir/packages") || return 125
    [[ -n $selection ]] || return 125
    mapfile -t packages <<< "$selection"
    case $mode in
        install) "$ADMIN" pacman -Syu --needed -- "${packages[@]}" ;;
        aur) "$helper" --sudo "$ADMIN" --sudoflags '' --nosudoloop --aur -S --needed -- "${packages[@]}" ;;
        uninstall) "$ADMIN" pacman -Rns -- "${packages[@]}" ;;
    esac
}

while true; do
    choice=$(printf '%s\n' 'Install — official repositories' 'AUR install — community packages' \
        'Uninstall — installed packages' 'Update everything' 'Close' |
        fzf --prompt='Packages > ' --header='Choose an action · Esc: close' \
            --no-multi --no-sort --height=12 --layout=reverse) || exit 0
    case $choice in
        'Install — official repositories') select_packages install ;;
        'AUR install — community packages') select_packages aur ;;
        'Uninstall — installed packages') select_packages uninstall ;;
        'Update everything') update_all ;;
        *) exit 0 ;;
    esac
    status=$?
    if ((status == 125)); then continue; fi
    if ((status == 130 || status == 143)); then exit "$status"; fi
    if ((status != 0)); then printf '\nThe operation did not finish successfully.\n' >&2; fi
    read -r -p $'\nPress Enter to return to the package menu…' _ || exit 0
done
