#!/usr/bin/env python3
"""Add desktop shortcuts or change keys, preserving surrounding configuration."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

from list_keybindings import collect, token_matches, unquote


MODIFIERS = {"ctrl": "Ctrl", "control": "Ctrl", "shift": "Shift",
             "alt": "Alt", "super": "Super", "mod": "Super", "win": "Super",
             "meta": "Super", "mod4": "Super"}
KEY_ALIASES = {"enter": "Return", "esc": "Escape", "pgup": "Page_Up",
               "pgdown": "Page_Down", ".": "period", ",": "comma",
               "-": "minus", "=": "equal", "/": "slash", "`": "grave"}


def normalize_key(value, group):
    value = value.strip()
    if not value or len(value) > 100 or not re.fullmatch(r"[A-Za-z0-9_+.,/`=\-]+", value):
        raise ValueError("Use a shortcut such as Super+Shift+A or Ctrl+Shift+F.")
    parts = value.split("+")
    if not parts[-1]:
        raise ValueError("Name the plus key 'plus', for example Ctrl+plus.")
    modifiers = []
    for part in parts[:-1]:
        mod = MODIFIERS.get(part.lower())
        if not mod or mod in modifiers:
            raise ValueError("Use Ctrl, Shift, Alt, or Super once each.")
        modifiers.append(mod)
    modifiers.sort()
    key = KEY_ALIASES.get(parts[-1].lower(), parts[-1])
    if group == "Desktop · Niri":
        modifiers = ["Mod" if m == "Super" else m for m in modifiers]
    elif len(key) == 1:
        key = key.lower()
    return "+".join(modifiers + [key])


def equivalent(value, group):
    try:
        return normalize_key(value, group).lower()
    except ValueError:
        return value.lower()


# Quality exception: Each user-editable field has a separate validation or serialization step and explanatory rejection path.
# Numeric ceilings are enforced by desktop/scripts/quality.py.
def save(request, config_dir):  # pylint: disable=too-many-branches,too-many-locals
    selected = request.get("binding", {})
    data = collect(config_dir)
    if data["error"]:
        raise ValueError("Could not check existing shortcuts. Refresh before saving.")
    binding = next((row for row in data["bindings"]
                    if row["source"] == selected.get("source")
                    and row["start"] == selected.get("start")
                    and row["rawKey"] == selected.get("rawKey")
                    and row["fingerprint"] == selected.get("fingerprint")), None)
    if not binding:
        raise ValueError("This configuration changed. Refresh the list and select the shortcut again.")
    if not binding["editable"]:
        raise ValueError("This mapping needs to be edited in its configuration file.")
    new_key = normalize_key(request.get("key", ""), binding["group"])
    if equivalent(new_key, binding["group"]) == equivalent(binding["rawKey"], binding["group"]):
        return {"ok": True, "message": "Shortcut unchanged."}
    for row in data["bindings"]:
        if row["group"] == binding["group"] and row != binding:
            if equivalent(row["rawKey"], row["group"]) == equivalent(new_key, binding["group"]):
                raise ValueError("That shortcut is already assigned to " + row["action"] + ".")
    target = Path(binding["source"]).resolve(strict=True)
    original = target.read_text()
    if hashlib.sha256(original.encode()).hexdigest() != binding["fingerprint"]:
        raise ValueError("This configuration changed. Refresh the list before saving.")
    source_guard = (target, original)
    replacement = json.dumps(new_key) if original[binding["start"]] == '"' else new_key
    if binding["group"] == "Desktop · Niri":
        declaration = replacement + original[binding["end"]:binding["declarationEnd"]]
        if target.name in {"keybindings-defaults.kdl", "keybindings-personal.kdl"}:
            target = target.with_name("keybindings-personal.kdl").resolve(strict=True)
            original = target.read_text()
        disabled = json.dumps(binding["rawKey"]) + ' hotkey-overlay-title=null { spawn "/usr/bin/true"; }'
        candidate = upsert_niri(original, binding["rawKey"], disabled)
        candidate = upsert_niri(candidate, new_key, declaration)
    else:
        start = original.rfind("\n", 0, binding["start"]) + 1
        end = original.find("\n", binding["end"])
        if end < 0:
            end = len(original)
        declaration = original[start:binding["start"]] + new_key + original[binding["end"]:end]
        if target.name in {"keybindings-defaults.conf", "keybindings-personal.conf"}:
            target = target.with_name("keybindings-personal.conf").resolve(strict=True)
            original = target.read_text()
        candidate = upsert_kitty(original, binding["rawKey"], "map " + binding["rawKey"] + " no_op")
        candidate = upsert_kitty(candidate, new_key, declaration)
    return persist(target, BindingChange(original, candidate, binding["group"], new_key, source_guard))


@dataclass(frozen=True)
class BindingChange:
    original: str
    candidate: str
    group: str
    key: str
    source_guard: tuple | None = None


def persist(target, change):
    original, candidate = change.original, change.candidate
    group, new_key, source_guard = change.group, change.key, change.source_guard
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=target.parent, prefix=".keybinding-check-", suffix=target.suffix, delete=False) as stream:
            stream.write(candidate)
            temporary = Path(stream.name)
        if group == "Desktop · Niri":
            checked = subprocess.run(["niri", "validate", "-c", str(temporary)], capture_output=True, timeout=15)
        else:
            # Kitty's own parser recognizes its key names and modifier aliases.
            code = "import sys; from kitty.options.utils import parse_shortcut; k=parse_shortcut(sys.stdin.readline().strip()); sys.exit(0 if k.key else 1)"
            checked = subprocess.run(["kitty", "+runpy", code], input=new_key + "\n", text=True, capture_output=True, timeout=15)
        if checked.returncode != 0:
            raise ValueError("That key combination is not valid for " + ("Niri" if group == "Desktop · Niri" else "Kitty") + ". Check the key name and try again.")
        if source_guard is not None and source_guard[0].read_text() != source_guard[1]:
            raise ValueError("This configuration changed while saving. Refresh and try again.")
        if target.read_text() != original:
            raise ValueError("This configuration changed while saving. Refresh and try again.")
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix="." + target.name + ".keybindings-backup-", delete=False) as backup:
            backup.write(original.encode())
            backup_path = backup.name
        os.chmod(temporary, stat.S_IMODE(target.stat().st_mode))
        os.replace(temporary, target)
        temporary = None
        message = "Shortcut saved. Niri applies it automatically."
        if group == "Terminal · Kitty":
            try:
                reloaded = subprocess.run(["pkill", "-SIGUSR1", "-x", "kitty"], capture_output=True, timeout=5)
                message = "Shortcut saved and Kitty configuration reloaded." if reloaded.returncode == 0 else "Shortcut saved. Kitty will use it when opened."
            except (OSError, subprocess.SubprocessError):
                message = "Shortcut saved. Open a new Kitty window to load it."
        return {"ok": True, "message": message, "backup": backup_path}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def add(request, config_dir):
    group = "Desktop · Niri"
    key = normalize_key(request.get("key", ""), group)
    command = request.get("command", "").strip()
    name = request.get("name", "").strip()
    if not command or len(command) > 4096 or any(c in command for c in "\n\r\0"):
        raise ValueError("Enter a command on one line, such as kitty or zen-browser.")
    if len(name) > 100 or any(c in name for c in "\n\r\0"):
        raise ValueError("Keep the shortcut name on one line, up to 100 characters.")
    data = collect(config_dir)
    if data["error"]:
        raise ValueError("Could not check existing shortcuts. Refresh before adding one.")
    for row in data["bindings"]:
        if row["group"] == group and equivalent(row["rawKey"], group) == equivalent(key, group):
            raise ValueError("That shortcut is already assigned to " + row["action"] + ".")
    personal = config_dir / "niri/keybindings-personal.kdl"
    target = (personal if personal.exists() else config_dir / "niri/config.kdl").resolve(strict=True)
    original = target.read_text()
    title = " hotkey-overlay-title=" + json.dumps(name, ensure_ascii=False) if name else ""
    line = "    " + json.dumps(key) + title + " { spawn \"sh\" \"-c\" " + json.dumps(command, ensure_ascii=False) + "; }\n"
    candidate = upsert_niri(original, key, line.strip())
    return persist(target, BindingChange(original, candidate, group, key))


def niri_declarations(text):
    """Locate complete bindings without treating braces in strings as syntax."""
    matches = token_matches(text)
    i, depth = 0, 0
    while i < len(matches):
        token = matches[i].group()
        if depth == 0 and token == "binds" and i + 1 < len(matches) and matches[i + 1].group() == "{":
            i += 2
            while i < len(matches) and matches[i].group() != "}":
                if matches[i].group() in ("\n", ";"):
                    i += 1
                    continue
                key = matches[i]
                i += 1
                while i < len(matches) and matches[i].group() not in ("{", "}"):
                    i += 1
                if i == len(matches) or matches[i].group() != "{":
                    break
                level = 1
                i += 1
                while i < len(matches) and level:
                    if matches[i].group() == "{": level += 1
                    elif matches[i].group() == "}": level -= 1
                    i += 1
                if level == 0:
                    yield unquote(key.group()), key.start(), matches[i - 1].end()
            i += 1
            continue
        if token == "{": depth += 1
        elif token == "}": depth -= 1
        i += 1


def upsert_niri(original, key, declaration):
    group = "Desktop · Niri"
    spans = [(start, end) for raw, start, end in niri_declarations(original)
             if equivalent(raw, group) == equivalent(key, group)]
    if not spans:
        return insert_niri(original, "    " + declaration + "\n")
    # Reuse disabled declarations and remove stale duplicates instead of adding
    # another node for the same key, which Niri rejects within a binds block.
    candidate = original
    for start, end in reversed(spans):
        candidate = candidate[:start] + (declaration if (start, end) == spans[0] else "") + candidate[end:]
    return candidate


def upsert_kitty(original, key, declaration):
    lines, replaced = [], False
    for line in original.splitlines(keepends=True):
        match = re.match(r"\s*map\s+(\S+)", line)
        if match and equivalent(match.group(1), "Terminal · Kitty") == equivalent(key, "Terminal · Kitty"):
            if not replaced:
                lines.append(declaration.rstrip() + "\n")
                replaced = True
        else:
            lines.append(line)
    result = "".join(lines)
    if not replaced:
        result = result.rstrip() + "\n" + declaration.rstrip() + "\n"
    return result


def insert_niri(original, line):
    # A KDL file may contain only one binds node. Insert in its existing block,
    # or create one locally when bindings are supplied by included profiles.
    matches = token_matches(original)
    depth = 0
    insertion = None
    in_binds = False
    for i, match in enumerate(matches):
        token = match.group()
        if depth == 0 and token == "binds" and i + 1 < len(matches) and matches[i + 1].group() == "{":
            in_binds = True
        if token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
            if in_binds and depth == 0:
                insertion = match.start()
                break
    if insertion is None:
        candidate = original + "\nbinds {\n" + line + "}\n"
    else:
        candidate = original[:insertion] + "\n" + line + original[insertion:]
    return candidate


if __name__ == "__main__":
    try:
        request = json.loads(sys.stdin.readline())
        config_dir = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        result = add(request, config_dir) if request.get("operation") == "add" else save(request, config_dir)
    except ValueError as error:
        result = {"ok": False, "error": str(error)}
    except (OSError, subprocess.SubprocessError):
        result = {"ok": False, "error": "Could not validate or save this shortcut. Check that its configuration file is writable."}
    print(json.dumps(result))
