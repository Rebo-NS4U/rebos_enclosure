#!/usr/bin/env bash
# Optional clone/update helper. Private repositories require existing Git authentication.
set -euo pipefail
repo_url=${REPO_URL:-https://github.com/Dytox2/rebos_enclosure.git}
clone_dir=${CLONE_DIR:-${INSTALL_ROOT:-$HOME/code}/rebos_enclosure}
branch=${BRANCH:-main}
die() { printf '%s\n' "$*" >&2; exit 1; }
if [[ ${1:-} == -h || ${1:-} == --help ]]; then
    cat <<'EOF'
Usage: bash oneline.sh [installer options]
Clone/update rebos_enclosure, then run its root install.sh.
Overrides: REPO_URL, CLONE_DIR, INSTALL_ROOT, BRANCH.
The repository is private: authenticate Git before using this helper.
This bootstrap creates/updates its checkout even when forwarding --dry-run.
For a completely read-only preview, run bash install.sh --dry-run in an existing clone.
EOF
    exit 0
fi
((EUID != 0)) || die 'Run this helper as your normal desktop user, without sudo.'
if ! command -v git >/dev/null; then
    [[ -f /etc/arch-release ]] || die 'Install Git first.'
    command -v sudo >/dev/null || die 'Install Git and configure sudo for your normal user first.'
    sudo pacman -Syu --needed git
fi
if [[ -d $clone_dir/.git ]]; then
    [[ $(git -C "$clone_dir" remote get-url origin) == "$repo_url" ]] || die 'Existing checkout has another origin. Set REPO_URL to match it, or choose a different CLONE_DIR.'
    [[ -z $(git -C "$clone_dir" status --porcelain) ]] || die 'Existing checkout has local edits. Run its install.sh directly or commit your changes before updating.'
    [[ $(git -C "$clone_dir" branch --show-current) == "$branch" ]] || die 'Existing checkout is on another branch. Run its install.sh directly or select the intended branch first.'
    git -C "$clone_dir" fetch origin "$branch"
    git -C "$clone_dir" merge --ff-only FETCH_HEAD
else
    [[ ! -e $clone_dir ]] || die "Destination already exists: $clone_dir"
    mkdir -p -- "$(dirname -- "$clone_dir")"
    git clone --depth=1 --branch "$branch" "$repo_url" "$clone_dir"
fi
if [[ -t 0 ]]; then
    exec bash "$clone_dir/install.sh" "$@"
elif { exec 3</dev/tty; } 2>/dev/null; then
    exec bash "$clone_dir/install.sh" "$@" <&3
else
    exec bash "$clone_dir/install.sh" "$@"
fi
