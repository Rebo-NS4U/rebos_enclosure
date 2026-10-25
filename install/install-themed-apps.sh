#!/usr/bin/env bash
# Finish integrations after opening Zen and Spotify on this machine.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec bash "$repo/desktop/scripts/finish-apps.sh" "$@"
