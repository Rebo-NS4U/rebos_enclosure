#!/usr/bin/env bash
# Assemble the portable login renderer without installing or starting services.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
build_dir=$(mktemp -d "${TMPDIR:-/tmp}/enclosure-build.XXXXXXXX")
trap 'rm -rf -- "$build_dir"' EXIT
python3 "$repo_root/desktop/scripts/prepare-quickshell-greeter.py" "$build_dir"
test -s "$build_dir/themes/enclosure/shell/modules/components/StyledRect.qml"
test -s "$build_dir/themes/enclosure/shell/modules/components/linear_gradient.frag.qsb"
printf '%s\n' 'Assembled Quickshell greeter and shared renderer successfully.'
