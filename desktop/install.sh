#!/usr/bin/env bash
# Install into an existing Arch system as the normal desktop user.
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# Direct desktop/ invocations must use the same freshness check as the root entry.
local_snapshot=0
installer_args=()
for argument in "$@"; do
    if [[ $argument == --local-snapshot ]]; then local_snapshot=1
    else installer_args+=("$argument")
    fi
done
if ((!local_snapshot)) && [[ ${REBOS_INSTALL_SNAPSHOT:-} != "$ROOT" ]]; then
    exec bash "$ROOT/../install.sh" "$@"
fi
set -- "${installer_args[@]}"
export PYTHONDONTWRITEBYTECODE=1
planner=(python3 "$ROOT/scripts/setup.py")
plan_args=()
dry_run=0
assume_yes=0
interactive=0
[[ $# != 0 || ! -t 0 ]] || interactive=1
work_dir=
trap '[[ -z ${work_dir:-} ]] || rm -rf -- "$work_dir"' EXIT
trap 'printf "Installer stopped at line %s. See the error above.\n" "$LINENO" >&2; if ((dry_run)); then printf "Dry-run mode does not change files or create backups.\n" >&2; fi' ERR

die() { printf '%s\n' "$*" >&2; exit 1; }
usage() {
    cat <<'EOF'
Usage: ./install.sh [options]
No arguments in a terminal opens the interactive setup menu.
  --interactive             Show setup choices (also works with --dry-run)
  --non-interactive          Use defaults/flags without the setup menu
  --profile core|full       Core desktop or full app selection (default: full)
  --groups LIST             all, none, or comma-separated app group IDs:
                            browser,communication,media,notes,recording,
                            development,utilities,video-wallpapers
  --graphics DRIVER         auto, keep, amd, intel, nvidia-open, nvidia-580,
                            nouveau, mesa (default: auto = Intel/AMD detection)
  --microcode CHOICE        auto, keep, amd, intel
  --kernel-headers LIST     Override detected DKMS kernel header packages
  --hybrid / --no-hybrid    Add/skip NVIDIA offload launcher with NVIDIA setup
  --early-kms               Early NVIDIA modules with mkinitcpio
  --monitors FILE           Monitor configuration JSON; see README
  --no-aur                  Skip optional AUR apps; incompatible with nvidia-580
  --no-login                Keep the current display manager
  --keep-network            Keep current network services
  --no-bluetooth            Skip Bluetooth packages/service configuration
  --no-power                Skip power-profiles-daemon setup
  --files-only              User files/monitor settings only; no system changes
  --dry-run                 Show the plan and verify payload; make no changes
                            Fetches selected source into temporary storage first
  --release TAG             Install an exact release tag, e.g. v1.3.1
                            Cannot combine with --local-snapshot or BRANCH
  --local-snapshot          Explicitly use this checkout without fetching
  --yes                     Accept plan; preserve AUR package review
  --help                    Show this help
EOF
}
while (($#)); do
    case $1 in
        --interactive) interactive=1 ;;
        --non-interactive) interactive=0 ;;
        --profile|--groups|--graphics|--microcode|--kernel-headers|--monitors)
            (($# >= 2)) || die "$1 needs a value"
            plan_args+=("$1" "$2"); shift ;;
        --no-login) plan_args+=(--login keep) ;;
        --keep-network) plan_args+=(--network keep) ;;
        --no-aur|--files-only|--no-bluetooth|--no-power|--hybrid|--no-hybrid|--early-kms) plan_args+=("$1") ;;
        --dry-run) dry_run=1 ;;
        --yes) assume_yes=1 ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown option: $1" ;;
    esac
    shift
done
command -v python3 >/dev/null || die 'Install Python first: sudo pacman -Syu --needed python'
[[ ${XDG_CONFIG_HOME:-$HOME/.config} == "$HOME/.config" && ${XDG_DATA_HOME:-$HOME/.local/share} == "$HOME/.local/share" && ${XDG_CACHE_HOME:-$HOME/.cache} == "$HOME/.cache" && ${XDG_STATE_HOME:-$HOME/.local/state} == "$HOME/.local/state" ]] || die 'Use standard XDG paths under HOME for this snapshot.'
if ((interactive)); then
    [[ -t 0 ]] || die 'Interactive setup needs a terminal. Use flags for unattended previews.'
    plan_args+=(--interactive)
fi
plan_json=$("${planner[@]}" plan "${plan_args[@]}")
plan() { printf '%s\n' "$plan_json" | "${planner[@]}" "$@"; }
mapfile -t settings < <(plan get login network bluetooth power graphics early_kms files_only hybrid)
login=${settings[0]}
network=${settings[1]}
bluetooth=${settings[2]}
power=${settings[3]}
graphics=${settings[4]}
early_kms=${settings[5]}
files_only=${settings[6]}
hybrid=${settings[7]}
mapfile -t packages < <(plan get packages)
mapfile -t aur_packages < <(plan get aur_packages)
plan summary
printf 'Destination: %s\n' "$HOME"
if ((dry_run)); then
    printf 'Dry-run mode: verify and preview only; no changes will be made.\n'
else
    printf 'Pre-install check: previewing changes before installation.\n'
fi
printf '%s\n' "$plan_json" | python3 "$ROOT/scripts/deploy.py" --dry-run --setup-stdin
if ((!files_only)); then plan check-drivers; fi
if ((dry_run)); then
    printf 'Dry run complete; no changes made. Run without --dry-run to install.\n'
    exit 0
fi
((EUID != 0)) || die 'Run as your normal desktop user, without sudo in front of ./install.sh'
if ((!files_only)); then
    [[ -f /etc/arch-release && $(uname -m) == x86_64 ]] || die 'Requires installed x86_64 Arch Linux'
    [[ ! -d /run/archiso ]] || die 'Boot the installed system first; do not run inside the live ISO'
    command -v sudo >/dev/null || die 'Configure sudo for your normal user first'
    if [[ $login == regreet && -L /etc/systemd/system/display-manager.service ]]; then
        active_manager=$(basename "$(readlink -f /etc/systemd/system/display-manager.service)")
        [[ $active_manager == greetd.service || $active_manager == ly@*.service || $active_manager == ly.service ]] || die "Existing display manager: $active_manager. Choose keep in the menu, or use --no-login."
    fi
fi
if ((!assume_yes)); then
    [[ -t 0 ]] || die 'Use --yes to accept the displayed plan without a terminal'
    read -r -p 'Install this plan? [y/N] ' response
    [[ $response == y || $response == Y ]] || exit 0
fi
if ((!files_only)); then
    sudo -v
    sudo pacman -Syu --needed --noconfirm python base-devel git curl rsync
    for package in "${packages[@]}"; do
        pacman -Si "$package" >/dev/null || die "Package unavailable: $package. Update the selection/package list and rerun."
    done
    sudo pacman -S --needed --noconfirm "${packages[@]}"
    if ((${#aur_packages[@]})); then
        if command -v paru >/dev/null; then aur_helper=paru
        elif command -v yay >/dev/null; then aur_helper=yay
        else
            work_dir=$(mktemp -d)
            git clone https://aur.archlinux.org/paru.git "$work_dir/paru"
            printf 'Review paru PKGBUILD before building:\n'
            cat "$work_dir/paru/PKGBUILD"
            read -r -p 'Build this paru package? [y/N] ' response
            [[ $response == y || $response == Y ]] || die 'AUR build declined; rerun with another selection or --no-aur'
            (cd "$work_dir/paru" && makepkg -si)
            rm -rf -- "$work_dir"
            work_dir=
            aur_helper=paru
        fi
        "$aur_helper" -S --needed "${aur_packages[@]}"
    fi
fi
for dependency in cc fish fc-cache; do command -v "$dependency" >/dev/null || die "Missing dependency: $dependency"; done
work_dir=$(mktemp -d)
if ((!files_only)) && [[ $login == regreet ]]; then
    cc -O2 -shared -fPIC "$ROOT/payload/system/rebos-greeter/cage-cursor.c" -ldl -o "$work_dir/cage-cursor.so"
    cc -O2 -shared -fPIC "$ROOT/payload/system/rebos-greeter/layout.c" $(pkg-config --cflags --libs gtk4) -o "$work_dir/layout.so"
fi
cc -O2 "$ROOT/payload/home/.local/share/cbonsai/cbonsai.c" -lpanelw -lncursesw -o "$work_dir/cbonsai"
# Validate the exact customized Niri configuration before changing user files.
python3 - "$ROOT/payload/home/.config/niri" "$work_dir/niri" <<'PY'
from pathlib import Path
import os
import shutil
import sys
shutil.copytree(sys.argv[1], sys.argv[2])
for path in Path(sys.argv[2]).rglob('*.kdl'):
    path.write_text(path.read_text().replace('@HOME@', os.environ['HOME']))
PY
plan render "$work_dir/niri"
if command -v niri >/dev/null; then niri validate -c "$work_dir/niri/config.kdl"; fi
printf '%s\n' "$plan_json" | python3 "$ROOT/scripts/deploy.py" --setup-stdin --cbonsai "$work_dir/cbonsai"
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$HOME/Pictures/Screenshots" "$HOME/code"
fc-cache -f "$HOME/.local/share/fonts"
if ((!files_only)); then
    xdg-user-dirs-update
    system_backup="/var/backups/rebos-desktop/$(date +%Y%m%d-%H%M%S)-$$"
    sudo mkdir -p "$system_backup"
    systemctl list-unit-files > "$work_dir/units-before.txt"
    sudo cp "$work_dir/units-before.txt" "$system_backup/units-before.txt"
    backup_system_file() {
        if [[ -e $1 || -L $1 ]]; then sudo cp -a --parents "$1" "$system_backup/"; fi
    }
    if [[ $graphics == nvidia-open || $graphics == nvidia-580 ]]; then
        backup_system_file /etc/modprobe.d/90-rebos-nvidia.conf
        printf 'options nvidia_drm modeset=1 fbdev=1\n' > "$work_dir/nvidia.conf"
        sudo install -Dm644 "$work_dir/nvidia.conf" /etc/modprobe.d/90-rebos-nvidia.conf
        if ((early_kms)); then
            backup_system_file /etc/mkinitcpio.conf.d/90-rebos-nvidia.conf
            printf 'MODULES+=(nvidia nvidia_modeset nvidia_uvm nvidia_drm)\n' > "$work_dir/early-kms.conf"
            sudo install -Dm644 "$work_dir/early-kms.conf" /etc/mkinitcpio.conf.d/90-rebos-nvidia.conf
        fi
        if command -v mkinitcpio >/dev/null; then sudo mkinitcpio -P; fi
    fi
    if [[ $login == regreet ]]; then
        for path in /etc/greetd /usr/local/lib/rebos-greeter /var/lib/rebos-greeter/theme /usr/share/icons/GoogleDot-Black; do
            backup_system_file "$path"
        done
        for name in config.toml regreet.toml; do
            sudo install -Dm644 "$ROOT/payload/system/greetd/$name" "/etc/greetd/$name"
        done
        for name in layout cage-cursor; do
            sudo install -Dm644 "$ROOT/payload/system/rebos-greeter/$name.c" "/usr/local/lib/rebos-greeter/$name.c"
            sudo install -Dm755 "$work_dir/$name.so" "/usr/local/lib/rebos-greeter/$name.so"
        done
        sudo install -d -m755 /var/lib/rebos-greeter/theme /usr/share/icons/GoogleDot-Black
        for name in regreet.css background.png glass-texture.png; do
            sudo install -m644 "$ROOT/payload/system/rebos-greeter/theme/$name" "/var/lib/rebos-greeter/theme/$name"
        done
        sudo cp -r "$ROOT/payload/home/.local/share/icons/GoogleDot-Black/." /usr/share/icons/GoogleDot-Black/
        sudo chown -R root:root /usr/share/icons/GoogleDot-Black
        # Change enablement for the next boot; never stop the running login/session.
        mapfile -t ly_units < <(systemctl list-unit-files 'ly*' --state=enabled --no-legend | awk '{print $1}')
        for unit in "${ly_units[@]}"; do
            sudo systemctl disable "$unit"
            if [[ $unit == ly@tty2.service ]]; then sudo systemctl enable getty@tty2.service; fi
        done
        sudo systemctl disable getty@tty1.service
        sudo systemctl enable greetd.service
    fi
    if [[ $network == networkmanager ]]; then
        sudo systemctl disable systemd-networkd.service systemd-networkd.socket systemd-networkd-wait-online.service iwd.service dhcpcd.service 2>/dev/null || true
        sudo systemctl enable NetworkManager.service
    fi
    if ((bluetooth)); then sudo systemctl enable bluetooth.service; fi
    if ((power)); then sudo systemctl enable power-profiles-daemon.service; fi
    systemctl --user daemon-reload || true
    systemctl --user enable pipewire.socket pipewire-pulse.socket wireplumber.service
    xdg-mime default thunar.desktop inode/directory
    xdg-settings set default-web-browser firefox.desktop
    if command -v zen-browser-bin >/dev/null || [[ -x /usr/bin/zen-browser || -x /usr/bin/zen ]]; then
        xdg-settings set default-web-browser zen-browser.desktop || true
    fi
    printf 'System backup: %s\n' "$system_backup"
fi
if ((!files_only)) && [[ $login == regreet ]]; then
    python3 "$ROOT/scripts/greeter_sync.py"
fi
printf '\nDesktop files installed. Selected plan: ~/.local/state/rebos-desktop/installation.json\n'
if ((!files_only)); then printf 'Reboot and choose Niri in your selected login setup.\n'; fi
printf 'Super+Return terminal | Super+Space launcher | Super+Shift+W wallpapers\n'
if ((hybrid)); then printf 'NVIDIA offload: rebos-prime-run <application>\n'; fi
printf 'After opening Zen/Spotify once: run bash desktop/scripts/finish-apps.sh from your Enclosure checkout.\n'
