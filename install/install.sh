#!/usr/bin/env bash
# Keep the former entry point on the same supported installation path.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec bash "$repo/install.sh" "$@"
