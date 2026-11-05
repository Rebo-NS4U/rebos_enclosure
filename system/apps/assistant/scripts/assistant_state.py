"""Persist the UI registry and recover bridges left alive after a UI crash."""
import json
import os
from pathlib import Path
import re
import sys
import tempfile


def load(path, runtime):
    try:
        state = json.loads(path.read_text())
        if not isinstance(state, dict):
            raise ValueError("Expected an object")
    except (OSError, ValueError):
        state = {}
    # A saved empty list means the user deliberately closed every tab.
    if "assistantSessionChannels" not in state:
        channels = []
        if runtime:
            directory = Path(runtime) / "rebos-assistant"
            try:
                live = Path("/proc/net/unix").read_text().splitlines()
                live_paths = {line.split()[-1] for line in live if len(line.split()) >= 8}
            except OSError:
                live_paths = set()
            for sock in sorted(directory.glob("acp*.sock")):
                if str(sock) not in live_paths:
                    continue
                channel = "default" if sock.name == "acp.sock" else sock.stem.removeprefix("acp-")
                if re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", channel):
                    channels.append(channel)
        if channels:
            state["assistantSessionChannels"] = channels
            state["assistantActiveChannel"] = channels[-1]
    return state


def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".states-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(state, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


if __name__ == "__main__":
    action, filename = sys.argv[1:3]
    if action == "load":
        print(json.dumps(load(Path(filename), os.environ.get("XDG_RUNTIME_DIR"))))
    elif action == "save":
        save(Path(filename), json.loads(sys.argv[3]))
    else:
        raise SystemExit("Unknown state operation")
