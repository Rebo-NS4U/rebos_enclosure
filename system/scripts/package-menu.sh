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

# Retain failures for diagnosis and retry only recognized recoverable errors.
run_packages() {
    if ((dry_run)); then run "$@"; return $?; fi
    local log status attempt=0 log_dir
    log_dir="${XDG_STATE_HOME:-$HOME/.local/state}/enclosure/packages"
    mkdir -p -- "$log_dir" || return 1
    log=$(mktemp "$log_dir/operation.XXXXXXXX.log") || return 1
    chmod 600 "$log"
    while true; do
        LC_ALL=C "$@" 2>&1 | tee -a "$log"
        status=${PIPESTATUS[0]}
        if ((status == 0 || status == 130 || status == 143 || attempt > 0)); then break; fi
        attempt=1
        if grep -Eq 'signature from .* is unknown trust|signature from .* is marginal trust|required key missing from keyring' "$log"; then
            printf '\nRefreshing Arch signing keys, then retrying once…\n'
            "$ADMIN" pacman -Sy --needed --noconfirm archlinux-keyring 2>&1 | tee -a "$log"
            status=${PIPESTATUS[0]}
            ((status == 0)) || break
        elif grep -Eqi 'failed retrieving file|Could not resolve host|Connection timed out|Operation too slow|The requested URL returned error: (404|502|503|504)' "$log"; then
            printf '\nDownload failed; retrying the operation once…\n'
        else
            break
        fi
    done
    if ((status != 0)); then
        printf '\nOperation failed (exit %s). Log: %s\n' "$status" "$log" >&2
        if grep -q 'failed to lock database' "$log"; then
            printf 'Another package manager may be running. Finish it before trying again.\n' >&2
        elif grep -Eq 'exists in filesystem|conflicting dependencies|breaks dependency' "$log"; then
            printf 'A package or file conflict needs attention; see the exact error above.\n' >&2
        fi
    else
        rm -f -- "$log"
    fi
    return "$status"
}

prepare_aur() {
    local missing
    # Builds run as the user; only installing prerequisites needs elevation.
    missing=$(pacman -T base-devel git 2>/dev/null)
    if [[ -n $missing ]]; then
        printf '\nInstalling AUR build prerequisites…\n'
        run_packages "$ADMIN" pacman -Syu --needed --noconfirm base-devel git || return $?
    fi
}

helper_options() {
    # Paru and Yay use different switches for their review menus.
    if [[ $1 == paru ]]; then
        helper_flags=(--skipreview --noupgrademenu)
    else
        helper_flags=(--answerclean None --answerdiff None --answerupgrade None)
    fi
}

update_all() {
    local helper result=0 status
    local -a helper_flags
    printf '\nUpdating Arch and AUR packages\n'
    if helper=$(aur_helper); then
        helper_options "$helper"
        run_packages "$helper" "${helper_flags[@]}" --sudo "$ADMIN" --sudoflags '' --nosudoloop -Syu --devel --noconfirm
    else
        printf 'No AUR helper found; updating official repositories only.\n'
        run_packages "$ADMIN" pacman -Syu --noconfirm
    fi
    status=$?
    if ((status == 130 || status == 143)); then return "$status"; fi
    if ((status != 0)); then printf 'Arch/AUR update failed.\n' >&2; result=1; fi
    if command -v flatpak >/dev/null; then
        printf '\nUpdating system Flatpaks\n'
        run "$ADMIN" flatpak update --system --noninteractive
        status=$?
        if ((status == 130 || status == 143)); then return "$status"; fi
        if ((status != 0)); then printf 'System Flatpak update failed.\n' >&2; result=1; fi
        printf '\nUpdating user Flatpaks\n'
        run flatpak update --user --noninteractive
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
    local -a packages picker helper_flags
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
    picker=(fzf --multi --height=100% --prompt='Packages > ' --header='Tab: select multiple · Enter: run (removals ask confirmation) · Esc: back'
        --preview "$preview" --preview-window 'down:60%:wrap'
        --bind 'alt-p:toggle-preview,alt-j:preview-down,alt-k:preview-up')
    selection=$("${picker[@]}" < "$work_dir/packages") || return 125
    [[ -n $selection ]] || return 125
    mapfile -t packages <<< "$selection"
    case $mode in
        install) run_packages "$ADMIN" pacman -Syu --needed --noconfirm -- "${packages[@]}" ;;
        aur) prepare_aur || return $?
            helper_options "$helper"
            run_packages "$helper" "${helper_flags[@]}" --sudo "$ADMIN" --sudoflags '' --nosudoloop -Syu --needed --noconfirm -- "${packages[@]}" ;;
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
    if ((status != 0)); then
        read -r -p $'\nPress Enter to return to the package menu…' _ || exit 0
    fi
done
