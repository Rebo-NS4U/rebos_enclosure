#!/usr/bin/env bash
# Fetch the current desktop without changing the caller's checkout.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for argument in "$@"; do
    case $argument in
        --local-snapshot|-h|--help)
            exec bash "$repo/desktop/install.sh" --local-snapshot "$@" ;;
    esac
done
command -v git >/dev/null || { printf '%s\n' 'Install Git before running the installer.' >&2; exit 1; }
snapshot_dir=$(mktemp -d -t rebos-install-XXXXXXXX)
trap 'rm -rf -- "$snapshot_dir"' EXIT
source_url=${REPO_URL:-https://github.com/Rebo-NS4U/rebos_enclosure.git}
clone_args=(clone --depth=1)
if [[ -n ${BRANCH:-} ]]; then clone_args+=(--branch "$BRANCH"); fi
printf 'Fetching the latest installer snapshot…\n'
if ! git "${clone_args[@]}" -- "$source_url" "$snapshot_dir/source"; then
    printf '%s\n' 'Installer stopped: could not fetch the latest source. No local fallback was installed.' >&2
    exit 1
fi
commit=$(git -C "$snapshot_dir/source" rev-parse HEAD)
printf 'Installing source revision: %s\n' "$commit"
REBOS_INSTALL_SNAPSHOT="$snapshot_dir/source/desktop" bash "$snapshot_dir/source/desktop/install.sh" "$@"
