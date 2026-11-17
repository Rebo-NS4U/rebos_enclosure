#!/usr/bin/env bash
# Remove only the retired GTK greeter; preserve greetd, Cage and the active session.
set -euo pipefail
[[ $EUID == 0 ]]
python3 - <<'PY'
import tomllib
from pathlib import Path
config = tomllib.loads(Path('/etc/greetd/config.toml').read_text())
assert 'quickshell/launcher' in config['default_session']['command'], 'Install Quickshell greeter first'
assert Path('/usr/local/lib/rebos-greeter/quickshell/themes/enclosure/shell/_qsgreet-main.qml').is_file()
PY
if pacman -Q greetd-regreet >/dev/null 2>&1; then
    pacman -R --noconfirm greetd-regreet
fi
rm -f /etc/greetd/regreet.toml /etc/greetd/regreet.toml.pacsave /var/lib/rebos-greeter/theme/regreet.css /var/lib/rebos-greeter/theme/glass-texture.png
rm -f /usr/local/lib/rebos-greeter/layout.c /usr/local/lib/rebos-greeter/layout.so
rm -f /usr/local/lib/rebos-greeter/cage-cursor.c /usr/local/lib/rebos-greeter/cage-cursor.c~ /usr/local/lib/rebos-greeter/cage-cursor.so /usr/local/lib/rebos-greeter/cage-cursor.so~
rm -f /usr/local/lib/rebos-greeter/icons/default/index.theme
printf '%s\n' 'Removed ReGreet and its GTK-only assets; greetd was not restarted.'
