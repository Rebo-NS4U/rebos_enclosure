#!/usr/bin/env bash
# Fetch the current desktop or a release without changing the caller's checkout.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
release=
local_snapshot=0
show_help=0
installer_args=()
while (($#)); do
    case $1 in
        --release)
            [[ $# -ge 2 && -n $2 && $2 != -* ]] || { printf '%s\n' '--release needs a tag, e.g. v1.3.0' >&2; exit 1; }
            release=$2; shift ;;
        --release=*)
            release=${1#*=}
            [[ -n $release && $release != -* ]] || { printf '%s\n' '--release needs a tag, e.g. v1.3.0' >&2; exit 1; } ;;
        --local-snapshot) local_snapshot=1; installer_args+=("$1") ;;
        -h|--help) show_help=1; installer_args+=("$1") ;;
        *) installer_args+=("$1") ;;
    esac
    shift
done
if ((show_help)); then
    exec bash "$repo/desktop/install.sh" --local-snapshot --help
fi
if [[ -n $release && ( $local_snapshot == 1 || -n ${BRANCH:-} ) ]]; then
    printf '%s\n' '--release cannot be combined with --local-snapshot or BRANCH.' >&2
    exit 1
fi
if ((local_snapshot)); then
    exec bash "$repo/desktop/install.sh" "${installer_args[@]}"
fi
command -v git >/dev/null || { printf '%s\n' 'Install Git before running the installer.' >&2; exit 1; }
if [[ -n $release ]]; then
    git check-ref-format "refs/tags/$release" || { printf '%s\n' 'Invalid release tag.' >&2; exit 1; }
fi
snapshot_dir=$(mktemp -d -t rebos-install-XXXXXXXX)
trap 'rm -rf -- "$snapshot_dir"' EXIT
source_url=${REPO_URL:-https://github.com/Rebo-NS4U/rebos_enclosure.git}
fetch_snapshot() {
    if [[ -n $release ]]; then
        printf 'Fetching installer release: %s\n' "$release"
        git init --quiet "$snapshot_dir/source" &&
            git -C "$snapshot_dir/source" fetch --depth=1 -- "$source_url" "refs/tags/$release" &&
            git -C "$snapshot_dir/source" checkout --quiet --detach FETCH_HEAD
    else
        clone_args=(clone --depth=1)
        if [[ -n ${BRANCH:-} ]]; then clone_args+=(--branch "$BRANCH"); fi
        printf 'Fetching the latest installer snapshot…\n'
        git "${clone_args[@]}" -- "$source_url" "$snapshot_dir/source"
    fi
}
if ! fetch_snapshot; then
    printf '%s\n' 'Installer stopped: could not fetch the requested source. No local fallback was installed.' >&2
    exit 1
fi
commit=$(git -C "$snapshot_dir/source" rev-parse HEAD)
printf 'Installing source revision: %s\n' "$commit"
REBOS_INSTALL_SNAPSHOT="$snapshot_dir/source/desktop" bash "$snapshot_dir/source/desktop/install.sh" "${installer_args[@]}"
