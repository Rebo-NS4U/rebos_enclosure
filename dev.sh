#!/usr/bin/env bash
# One development entrypoint, from any working directory.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export PYTHONDONTWRITEBYTECODE=1
exec python3 "$ROOT/desktop/scripts/develop.py" "$@"
