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
install -Dm644 "$ROOT/system/etc/greetd/config.toml" /etc/greetd/config.toml
bash "$ROOT/desktop/scripts/remove-regreet.sh"
printf 'Quickshell greeter configured for next login. Backup: %s/config.toml\n' "$backup"
