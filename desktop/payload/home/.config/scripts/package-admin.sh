#!/usr/bin/env bash
# AUR helpers can check sudo's timestamp, but every actual command is approved.
set -euo pipefail
if (($# == 1)) && [[ $1 == -v || $1 == -k ]]; then
    exit 0
fi
[[ ${1:-} != -- ]] || shift
if (($# == 0)) || [[ $1 == -* ]]; then
    printf 'Unsupported administrator request from the package helper.\n' >&2
    exit 2
fi
exec "$HOME/.local/bin/assistant-sudo" --reason \
    'Apply the selected package operation; review the exact command below' -- "$@"
