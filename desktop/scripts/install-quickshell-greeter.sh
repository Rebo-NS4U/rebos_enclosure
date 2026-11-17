#!/usr/bin/env bash
# Install reviewed portable source. Run as root; does not restart greetd.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
SOURCE="$ROOT/system/etc/rebos-greeter/quickshell"
TARGET=/usr/local/lib/rebos-greeter/quickshell
[[ $EUID == 0 ]] || { echo 'Run using assistant-sudo or sudo' >&2; exit 1; }
for dependency in quickshell cage greetd python3; do command -v "$dependency" >/dev/null; done
backup="/var/backups/rebos-greeter/$(date +%Y%m%d-%H%M%S)"
install -d -m755 "$backup" "$TARGET"
cp -a /etc/greetd/config.toml "$backup/config.toml"
python3 "$ROOT/desktop/scripts/prepare-quickshell-greeter.py" "$TARGET"
chown -R root:root "$TARGET"
chmod -R a+rX "$TARGET"
chmod 755 "$TARGET/launcher"
# Keep the existing ReGreet payload and config for manual rollback.
install -Dm644 /dev/stdin /etc/greetd/config.toml <<'CONFIG'
[terminal]
vt = 1

[default_session]
command = "env QSGREET_PREFIX=/usr/local/lib/rebos-greeter/quickshell QSGREET_THEME=enclosure QSGREET_LOCK_USER=0 XCURSOR_THEME=GoogleDot-Black XCURSOR_SIZE=20 /usr/local/lib/rebos-greeter/quickshell/launcher"
user = "greeter"
CONFIG
printf 'Quickshell greeter configured for next login. Backup: %s/config.toml\n' "$backup"
