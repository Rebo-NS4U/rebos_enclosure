#!/usr/bin/env python3
"""Read or change the laptop's explicit Niri lid-close suspend override."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from window_rules import write_validated


def has_lid(input_devices):
    for capability in input_devices.glob("input*/capabilities/sw"):
        try:
            # sysfs lists words most significant first. SW_LID is bit zero.
            if int(capability.read_text().split()[-1], 16) & 1:
                return True
        except (OSError, ValueError, IndexError):
            continue
    return False


def settings(action, config_dir, input_devices):
    result = {"laptop": has_lid(input_devices), "enabled": False}
    if not result["laptop"]:
        return result

    path = config_dir / "niri/config.kdl"
    fragment = config_dir / "quickshell/scripts/lid-suspend.kdl"
    include = f'include optional=true {json.dumps(str(fragment), ensure_ascii=False)} // Enclosure lid suspend'
    try:
        original = path.read_text()
        lines = original.splitlines(keepends=True)
        enabled = any(line.rstrip("\r\n") == include for line in lines)
        result["enabled"] = enabled
        if action == "enable" and not enabled:
            if not fragment.is_file():
                raise ValueError("The lid suspend configuration is missing.")
            separator = "" if original.endswith("\n") or not original else "\n"
            write_validated(path, original, original + separator + include + "\n")
            result["enabled"] = True
        elif action == "disable" and enabled:
            candidate = "".join(line for line in lines if line.rstrip("\r\n") != include)
            write_validated(path, original, candidate)
            result["enabled"] = False
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result["error"] = str(error)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "enable", "disable"))
    action = parser.parse_args().action
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    print(json.dumps(settings(action, config_dir, Path("/sys/class/input"))))


if __name__ == "__main__":
    main()
