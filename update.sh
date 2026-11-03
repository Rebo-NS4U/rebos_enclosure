#!/usr/bin/env bash
# Use the updater belonging to the live desktop, even from an older checkout.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
updater=$(python3 -c '
from pathlib import Path
import subprocess
import sys

local = Path(sys.argv[1]).resolve()
home = Path.home()
checkouts = set()
for relative in (".config/quickshell", "code/rebos-assistant", "code/anime-streamer"):
    link = home / relative
    if not link.is_symlink():
        continue
    target = link.resolve()
    for parent in target.parents:
        if (parent / ".git").exists() and ((parent / "system") in target.parents or (parent / "desktop/payload/home") in target.parents):
            checkouts.add(parent)
            break
    else:
        if "desktop/payload/home" in str(target):
            sys.exit(f"Update stopped: Missing source checkout: {target}")
if len(checkouts) > 1:
    sys.exit("Update stopped: Application links point to different checkouts")
checkout = next(iter(checkouts), local)
if checkout != local:
    def origin(path):
        return subprocess.check_output(["git", "-C", str(path), "remote", "get-url", "origin"], text=True).strip()
    if origin(checkout) != origin(local):
        sys.exit("Update stopped: Launcher repository differs from the installed checkout origin")
updater = checkout / "desktop/scripts/update.py"
if not updater.is_file():
    sys.exit(f"Update stopped: Missing installed updater: {updater}")
print(updater)
' "$repo")
exec python3 "$updater" "$@"
