#!/usr/bin/env bash
# Refresh user settings from the current snapshot, with backups.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec bash "$repo/install.sh" --files-only "$@"
