#!/usr/bin/env bash
# Compile every shipped native helper without installing or loading it.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
build_dir=$(mktemp -d "${TMPDIR:-/tmp}/enclosure-build.XXXXXXXX")
trap 'rm -rf -- "$build_dir"' EXIT

bash "$repo_root/desktop/scripts/build-greeter-cursor.sh" "$build_dir/cage-cursor.so"
read -r -a gtk_flags <<< "$(pkg-config --cflags --libs gtk4)"
cc -O2 -shared -fPIC "$repo_root/system/etc/rebos-greeter/layout.c" "${gtk_flags[@]}" -o "$build_dir/layout.so"

for artifact in cage-cursor.so layout.so; do
    test -s "$build_dir/$artifact"
done
wlr_package=$(ldd "$(command -v cage)" | sed -n 's/.*lib\(wlroots[^ ]*\)\.so .*/\1/p')
read -r -a wlr_flags <<< "$(pkg-config --cflags --libs "$wlr_package" wayland-server)"
mkdir "$build_dir/test"
cc -O2 -Wall -Wextra -Werror "$repo_root/desktop/tests/native/greeter-cursor.c" "${wlr_flags[@]}" -ldl -o "$build_dir/test/cage"
XCURSOR_PATH="$repo_root/system/share/icons" "$build_dir/test/cage"
"$build_dir/test/cage" native
printf '%s\n' 'Built greeter extensions and verified cursor-shape handling successfully.'
