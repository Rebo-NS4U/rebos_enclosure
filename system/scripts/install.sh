#!/usr/bin/env bash
# Compatibility entry point: all package actions share one menu.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec bash "$SCRIPT_DIR/package-menu.sh" "$@"
