#!/usr/bin/env bash
# Public entry point for the complete rebos desktop installer.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec bash "$repo/desktop/install.sh" "$@"
