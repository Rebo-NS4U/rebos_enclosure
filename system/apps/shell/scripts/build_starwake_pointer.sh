#!/usr/bin/env bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
build_dir="${XDG_CACHE_HOME:-$HOME/.cache}/rebos_shell/starwake-pointer"
mkdir -p "$build_dir"
pkg-config --atleast-version=6.9 Qt6Quick || { echo 'Starwake pointer confinement requires Qt 6.9 or newer.' >&2; exit 1; }
protocol="$(pkg-config --variable=pkgdatadir wayland-protocols)/unstable/pointer-constraints/pointer-constraints-unstable-v1.xml"
fingerprint=$(sha256sum "$source_dir/starwake_pointer.cpp" "$source_dir/build_starwake_pointer.sh" "$protocol" /usr/lib/libQt6Gui.so.6 /usr/lib/libQt6Quick.so.6)
if [[ ! -f "$build_dir/libstarwake-pointer.so" || ! -f "$build_dir/fingerprint" || "$(cat "$build_dir/fingerprint")" != "$fingerprint" ]]; then
    temporary=$(mktemp -d "$build_dir/.build.XXXXXX")
    trap 'rm -rf -- "$temporary"' EXIT
    wayland-scanner client-header "$protocol" "$temporary/pointer-constraints.h"
    wayland-scanner private-code "$protocol" "$temporary/pointer-constraints.c"
    read -r -a flags <<< "$(pkg-config --cflags --libs Qt6Quick wayland-client)"
    gcc -fPIC -c "$temporary/pointer-constraints.c" -o "$temporary/protocol.o"
    g++ -std=c++17 -shared -fPIC -Wall -Wextra -I"$temporary" "$source_dir/starwake_pointer.cpp" "$temporary/protocol.o" "${flags[@]}" -o "$temporary/library.so"
    mv -f "$temporary/library.so" "$build_dir/libstarwake-pointer.so"
    printf '%s\n' "$fingerprint" > "$temporary/fingerprint"
    mv -f "$temporary/fingerprint" "$build_dir/fingerprint"
fi
printf '%s\n' "$build_dir/libstarwake-pointer.so"
