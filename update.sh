#!/usr/bin/env bash
# Fetch and apply the current GitHub desktop without resetting user settings.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$repo/desktop/scripts/update.py" "$@"
