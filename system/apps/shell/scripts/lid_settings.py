#!/usr/bin/env python3
"""Read or change the laptop's Niri lid-close action."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess

from window_rules import write_validated

ACTIONS = {
    "default": ("System default", None),
    "nothing": ("Do nothing", None),
    "lock": ("Lock screen", None),
    "sleep": ("Sleep (system chooses mode)", "CanSleep"),
    "suspend": ("Suspend", "CanSuspend"),
    "hibernate": ("Hibernate", "CanHibernate"),
    "hybrid-sleep": ("Hybrid sleep", "CanHybridSleep"),
    "suspend-then-hibernate": ("Suspend, then hibernate", "CanSuspendThenHibernate"),
    "poweroff": ("Shut down", "CanPowerOff"),
}
MARKER = " // Enclosure lid action"


def has_lid(input_devices):
    for capability in input_devices.glob("input*/capabilities/sw"):
        try:
            # sysfs lists words most significant first. SW_LID is bit zero.
            if int(capability.read_text().split()[-1], 16) & 1:
                return True
        except (OSError, ValueError, IndexError):
            continue
    return False


def is_available(method):
    if method is None:
        return True
    interface = "org.freedesktop.login1"
    try:
        command = ["busctl", "--timeout=2s", "call", interface, "/org/freedesktop/login1",
                   interface + ".Manager", method]
        response = subprocess.run(command, capture_output=True, check=True, text=True, timeout=3)
        return response.stdout.strip() in {'s "yes"', 's "inhibited"', 's "inhibitor-blocked"'}
    except (OSError, subprocess.SubprocessError):
        return False


def saved_action(config_dir, requested, available):
    path = config_dir / "niri/config.kdl"
    scripts = config_dir / "quickshell/scripts"
    fragments = {action: scripts / "lid-actions" / f"{action}.kdl" for action in ACTIONS}
    fragments["suspend"] = scripts / "lid-suspend.kdl"
    includes = {
        action: f'include optional=true {json.dumps(str(fragment), ensure_ascii=False)}{MARKER}'
        for action, fragment in fragments.items() if action != "default"
    }
    managed = {line: action for action, line in includes.items()}
    managed[includes["suspend"].removesuffix(MARKER) + " // Enclosure lid suspend"] = "suspend"
    result = {"action": "default"}
    try:
        original = path.read_text()
        lines = original.splitlines(keepends=True)
        result["action"] = next(
            (managed[line.rstrip("\r\n")] for line in reversed(lines) if line.rstrip("\r\n") in managed),
            "default",
        )
        if requested == "status" or requested == result["action"]:
            return result
        if requested not in available:
            raise ValueError("This lid action is unavailable on this laptop.")
        candidate = "".join(line for line in lines if line.rstrip("\r\n") not in managed)
        if requested != "default":
            if not fragments[requested].is_file():
                raise ValueError("The lid action configuration is missing.")
            separator = "\n" if candidate and not candidate.endswith("\n") else ""
            candidate += separator + includes[requested] + "\n"
        write_validated(path, original, candidate)
        result["action"] = requested
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result["error"] = str(error)
    return result


def settings(requested, config_dir, input_devices):
    if not has_lid(input_devices):
        return {"laptop": False}

    with ThreadPoolExecutor() as workers:
        supported = workers.map(is_available, (method for _, method in ACTIONS.values()))
        available = [action for action, supported_action in zip(ACTIONS, supported) if supported_action]
    result = saved_action(config_dir, requested, available)
    # Keep displaying the saved value if support changes, such as after swap is removed.
    options = [{"value": action, "label": label if action in available else label + " (unavailable)"}
               for action, (label, _) in ACTIONS.items() if action in available or action == result["action"]]
    return {"laptop": True, "options": options, **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", *ACTIONS))
    action = parser.parse_args().action
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    print(json.dumps(settings(action, config_dir, Path("/sys/class/input"))))


if __name__ == "__main__":
    main()
