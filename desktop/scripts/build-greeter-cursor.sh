#!/usr/bin/env bash
# Match Cage's wlroots ABI; never guess from whichever headers are newest.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
wlr_package=$(ldd "$(command -v cage)" | sed -n 's/.*lib\(wlroots[^ ]*\)\.so .*/\1/p')
[[ -n $wlr_package ]] || { echo 'Cannot identify Cage wlroots ABI' >&2; exit 1; }
read -r -a flags <<< "$(pkg-config --cflags --libs "$wlr_package" wayland-server)"
cc -O2 -Wall -Wextra -Werror -shared -fPIC "$repo_root/system/etc/rebos-greeter/cage-cursor.c" "${flags[@]}" -ldl -o "$1"
