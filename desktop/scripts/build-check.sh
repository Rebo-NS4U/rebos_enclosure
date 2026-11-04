#!/usr/bin/env bash
# Compile every shipped native helper without installing or loading it.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
build_dir=$(mktemp -d "${TMPDIR:-/tmp}/enclosure-build.XXXXXXXX")
trap 'rm -rf -- "$build_dir"' EXIT

cc -O2 "$repo_root/system/share/cbonsai/cbonsai.c" -lpanelw -lncursesw -o "$build_dir/cbonsai"
cc -O2 -shared -fPIC "$repo_root/system/etc/rebos-greeter/cage-cursor.c" -ldl -o "$build_dir/cage-cursor.so"
read -r -a gtk_flags <<< "$(pkg-config --cflags --libs gtk4)"
cc -O2 -shared -fPIC "$repo_root/system/etc/rebos-greeter/layout.c" "${gtk_flags[@]}" -o "$build_dir/layout.so"

for artifact in cbonsai cage-cursor.so layout.so; do
    test -s "$build_dir/$artifact"
done
printf '%s\n' 'Built cbonsai, cage-cursor.so and layout.so successfully.'
