#!/usr/bin/env bash
# Install the current snapshot's user files without changing packages or services.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec bash "$repo/install.sh" --files-only "$@"
