#!/usr/bin/env bash
# Optional setup: active-session access for the bar's physical input controls.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
"$HOME/.local/bin/assistant-sudo" --reason 'Enable active-session keyboard and touchscreen toggles' -- /usr/bin/install -m 644 "$root/system/apps/shell/scripts/70-enclosure-input-controls.rules" /etc/udev/rules.d/70-enclosure-input-controls.rules
"$HOME/.local/bin/assistant-sudo" --reason 'Load the input-toggle access rule' -- /usr/bin/udevadm control --reload-rules
"$HOME/.local/bin/assistant-sudo" --reason 'Apply input-toggle access to connected devices without restarting the desktop' -- /usr/bin/udevadm trigger --subsystem-match=input --action=change
