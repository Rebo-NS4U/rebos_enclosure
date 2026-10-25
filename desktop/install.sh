#!/usr/bin/env bash
# Run from the installed Arch system as a regular sudo-capable user.
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
profile=full
dry_run=0
files_only=0
login=1
network=1
aur=1
assume_yes=0
work_dir=
trap '[[ -z ${work_dir:-} ]] || rm -rf -- "$work_dir"' EXIT
trap 'printf "Installer stopped at line %s. See the error above. Dry-run mode does not change files or create backups.\n" "$LINENO" >&2' ERR

die() { printf '%s\n' "$*" >&2; exit 1; }
usage() {
    cat <<'EOF'
Usage: ./install.sh [options]
  --profile core|full   Core desktop, or desktop plus apps (default: full)
  --no-aur              Skip optional AUR packages (Firefox remains available)
  --no-login            Keep current display-manager configuration
  --keep-network       Keep current network services; still installs NetworkManager
  --files-only         Deploy user files only; no sudo, packages or services
  --dry-run            Verify payload and print plan; make no changes
  --yes                Accept this install plan (AUR review remains interactive)
  --help               Show this help
EOF
}
while (($#)); do
    case $1 in
        --profile) (($# >= 2)) || die '--profile needs a value'; profile=$2; shift ;;
        --no-aur) aur=0 ;;
        --no-login) login=0 ;;
        --keep-network) network=0 ;;
        --files-only) files_only=1 ;;
        --dry-run) dry_run=1 ;;
        --yes) assume_yes=1 ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown option: $1" ;;
    esac
    shift
done
[[ $profile == core || $profile == full ]] || die 'Profile must be core or full'
[[ ${XDG_CONFIG_HOME:-$HOME/.config} == "$HOME/.config" && ${XDG_DATA_HOME:-$HOME/.local/share} == "$HOME/.local/share" && ${XDG_CACHE_HOME:-$HOME/.cache} == "$HOME/.cache" && ${XDG_STATE_HOME:-$HOME/.local/state} == "$HOME/.local/state" ]] || die 'This snapshot uses standard XDG paths under HOME. Unset custom XDG paths before installation.'

read_packages() { awk '{sub(/#.*/, ""); if (NF) print $1}' "$@" | sort -u; }
lists=("$ROOT/packages/core.txt")
[[ $profile != full ]] || lists+=("$ROOT/packages/apps.txt")
hardware=()
if [[ -r /proc/cpuinfo ]]; then
    if grep -q GenuineIntel /proc/cpuinfo; then hardware+=(intel-ucode); fi
    if grep -q AuthenticAMD /proc/cpuinfo; then hardware+=(amd-ucode); fi
fi
# Kernel-provided drivers and Mesa work across AMD/Intel. NVIDIA drivers are an explicit hardware choice.
for vendor in /sys/class/drm/card*/device/vendor; do
    [[ -r $vendor ]] || continue
    case $(<"$vendor") in
        0x1002) hardware+=(vulkan-radeon libva-mesa-driver) ;;
        0x8086) hardware+=(vulkan-intel intel-media-driver) ;;
        0x10de) printf 'NVIDIA detected: keep/install the driver appropriate to your GPU and kernel; see README.\n' ;;
    esac
done
mapfile -t packages < <(read_packages "${lists[@]}")
packages+=("${hardware[@]}")
printf 'rebos desktop installer\nProfile: %s | AUR: %s | Ly: %s | NetworkManager: %s\nDestination: %s\n' "$profile" "$aur" "$login" "$network" "$HOME"
printf 'Official packages: %s\n' "${packages[*]}"
if [[ $profile == full && $aur == 1 ]]; then
    printf 'AUR packages: %s\n' "$(read_packages "$ROOT/packages/aur.txt" | paste -sd ' ')"
fi
if ((dry_run)); then
    command -v python3 >/dev/null || die 'Install python first to verify the payload'
    python3 "$ROOT/scripts/deploy.py" --dry-run
    exit 0
fi
((EUID != 0)) || die 'Run as the desktop user, without sudo in front of ./install.sh'
if ((!files_only)); then
    [[ -f /etc/arch-release && $(uname -m) == x86_64 ]] || die 'Requires installed x86_64 Arch Linux'
    [[ ! -d /run/archiso ]] || die 'Boot the installed Arch system first; do not run in the live ISO'
    command -v sudo >/dev/null || die 'Install sudo and grant your normal user access first (README)'
    if ((login)) && [[ -L /etc/systemd/system/display-manager.service ]]; then
        active_manager=$(basename "$(readlink -f /etc/systemd/system/display-manager.service)")
        [[ $active_manager == ly@*.service || $active_manager == ly.service ]] || die "Existing display manager: $active_manager. Rerun with --no-login or disable it explicitly."
    fi
fi
if ((!assume_yes)); then
    [[ -t 0 ]] || die 'Use --yes to accept the displayed plan in unattended use'
    read -r -p 'Install the displayed desktop configuration? [y/N] ' response
    [[ $response == y || $response == Y ]] || exit 0
fi
if ((!files_only)); then
    sudo -v
    # Always perform a full upgrade; never create a partial-upgrade installation.
    sudo pacman -Syu --needed --noconfirm python base-devel git curl rsync
fi
command -v python3 >/dev/null || die 'python3 is required'
python3 "$ROOT/scripts/deploy.py" --verify
python3 "$ROOT/scripts/deploy.py" --dry-run
if ((!files_only)); then
    # Fail on removed/renamed repo packages before installing the profile.
    for package in "${packages[@]}"; do
        pacman -Si "$package" >/dev/null || die "Package unavailable: $package. Update the package list and rerun."
    done
    sudo pacman -S --needed --noconfirm "${packages[@]}"
    if [[ $profile == full && $aur == 1 ]]; then
        if command -v paru >/dev/null; then
            aur_helper=paru
        elif command -v yay >/dev/null; then
            aur_helper=yay
        else
            work_dir=$(mktemp -d)
            git clone https://aur.archlinux.org/paru.git "$work_dir/paru"
            printf 'Review paru PKGBUILD before building:\n'
            cat "$work_dir/paru/PKGBUILD"
            read -r -p 'Build this paru package? [y/N] ' response
            [[ $response == y || $response == Y ]] || die 'AUR build declined; rerun with --no-aur if desired'
            (cd "$work_dir/paru" && makepkg -si)
            rm -rf -- "$work_dir"
            work_dir=
            aur_helper=paru
        fi
        mapfile -t aur_packages < <(read_packages "$ROOT/packages/aur.txt")
        "$aur_helper" -S --needed "${aur_packages[@]}"
    fi
fi
for dependency in cc fish fc-cache; do
    command -v "$dependency" >/dev/null || die "Missing dependency: $dependency"
done
work_dir=$(mktemp -d)
cc -O2 "$ROOT/payload/home/.local/share/cbonsai/cbonsai.c" -lpanelw -lncursesw -o "$work_dir/cbonsai"
# Check config with the target compositor before replacing any user settings.
if command -v niri >/dev/null; then
    python3 - "$ROOT/payload/home/.config/niri/config-quickshell.kdl" "$work_dir/niri.kdl" <<'PY'
from pathlib import Path
import os
import sys
Path(sys.argv[2]).write_text(Path(sys.argv[1]).read_text().replace('@HOME@', os.environ['HOME']))
PY
    niri validate -c "$work_dir/niri.kdl"
fi
python3 "$ROOT/scripts/deploy.py" --cbonsai "$work_dir/cbonsai"
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$HOME/Pictures/Screenshots" "$HOME/code"
fc-cache -f "$HOME/.local/share/fonts"
if ((!files_only)); then
    xdg-user-dirs-update
    system_backup="/var/backups/rebos-desktop/$(date +%Y%m%d-%H%M%S)-$$"
    sudo mkdir -p "$system_backup"
    systemctl list-unit-files > "$work_dir/units-before.txt"
    sudo cp "$work_dir/units-before.txt" "$system_backup/units-before.txt"
    if ((login)); then
        if [[ -d /etc/ly ]]; then sudo cp -a /etc/ly "$system_backup/ly"; fi
        sudo install -Dm644 "$ROOT/payload/system/ly/config.ini" /etc/ly/config.ini
        sudo install -Dm644 "$ROOT/payload/system/ly/blackhole-smooth-240x67.dur" /etc/ly/blackhole-smooth-240x67.dur
        sudo systemctl disable getty@tty2.service
        sudo systemctl enable ly@tty2.service
    fi
    if ((network)); then
        # Changes take effect at reboot; do not cut off the current installation connection.
        sudo systemctl disable systemd-networkd.service systemd-networkd.socket systemd-networkd-wait-online.service iwd.service dhcpcd.service 2>/dev/null || true
        sudo systemctl enable NetworkManager.service
    fi
    sudo systemctl enable bluetooth.service power-profiles-daemon.service
    systemctl --user daemon-reload || true
    systemctl --user enable pipewire.socket pipewire-pulse.socket wireplumber.service
    xdg-mime default thunar.desktop inode/directory
    xdg-settings set default-web-browser firefox.desktop
    if command -v zen-browser-bin >/dev/null || [[ -x /usr/bin/zen-browser || -x /usr/bin/zen ]]; then
        xdg-settings set default-web-browser zen-browser.desktop || true
    fi
    printf 'System backup: %s\n' "$system_backup"
fi
printf '\nDesktop installed. Reboot, select Niri at login, then press Super+Return.\n'
printf 'Super+Space launcher | Super+Shift+W wallpapers | Super+Alt+L lock\n'
printf 'For Spotify/Zen integration after first launch: bash "%s/scripts/finish-apps.sh"\n' "$ROOT"
