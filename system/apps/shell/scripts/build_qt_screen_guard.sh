#!/usr/bin/env bash
set -euo pipefail

# This private-ABI workaround has only been verified with Qt 6.12.0.
# Other Qt versions and machines without a compiler use unmodified Qt.
for dependency in pkg-config g++ sha256sum; do
    command -v "$dependency" >/dev/null || exit 0
done
version=$(pkg-config --modversion Qt6Core 2>/dev/null) || exit 0
[[ "$version" == "6.12.0" ]] || exit 0
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
guard_dir="${XDG_DATA_HOME:-$HOME/.local/share}/rebos_shell/qt-screen-guard"
if [[ -f "$guard_dir/build-make/librebos-qt-screen-guard.so" ]] \
    && sha256sum --check --status "$guard_dir/qt-libraries.sha256" 2>/dev/null \
    && sha256sum --check --status "$guard_dir/source.sha256" 2>/dev/null; then
    exit 0
fi
mkdir -p "$guard_dir/build-make"
temporary=$(mktemp -d "$guard_dir/.build.XXXXXX")
trap 'rm -rf -- "$temporary"' EXIT
includes=()
for module in QtCore QtGui QtWaylandClient QtWaylandGlobal; do
    includes+=("-I/usr/include/qt6/$module/$version" "-I/usr/include/qt6/$module/$version/$module")
done
read -r -a qt_flags <<< "$(pkg-config --cflags --libs Qt6WaylandClient Qt6Gui)"
g++ -std=c++17 -fPIC -shared -Wall -Wextra "$source_dir/qt_screen_guard.cpp" \
    "${includes[@]}" "${qt_flags[@]}" -ldl -o "$temporary/guard.so"
sha256sum /usr/lib/libQt6Core.so.6 /usr/lib/libQt6Gui.so.6 /usr/lib/libQt6WaylandClient.so.6 > "$temporary/qt-libraries.sha256"
sha256sum "$source_dir/qt_screen_guard.cpp" "$source_dir/build_qt_screen_guard.sh" > "$temporary/source.sha256"
# Replace atomically: an existing panel may still have the previous file mapped.
mv -f "$temporary/guard.so" "$guard_dir/build-make/librebos-qt-screen-guard.so"
mv -f "$temporary/qt-libraries.sha256" "$guard_dir/qt-libraries.sha256"
mv -f "$temporary/source.sha256" "$guard_dir/source.sha256"
