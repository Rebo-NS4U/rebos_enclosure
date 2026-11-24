"""Select a Niri workspace by its persistent IPC ID, including across outputs."""
import json
import os
import socket
import sys

with socket.socket(socket.AF_UNIX) as ipc:
    ipc.settimeout(2)
    ipc.connect(os.environ["NIRI_SOCKET"])
    request = {"Action": {"FocusWorkspace": {"reference": {"Id": int(sys.argv[1])}}}}
    ipc.sendall(json.dumps(request).encode() + b"\n")
    reply = json.loads(ipc.makefile("rb").readline())
    if "Err" in reply:
        sys.exit(str(reply["Err"]))
