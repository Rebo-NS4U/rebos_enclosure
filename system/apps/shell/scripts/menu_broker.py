#!/usr/bin/env python3
"""Private in-memory selection bridge. Never writes menu or clipboard data to disk."""
import json
import os
from pathlib import Path
import selectors
import socket
import sys


def bind_server():
    path = Path(os.environ["XDG_RUNTIME_DIR"]) / "rebos-shell-menu.sock"
    if path.exists():
        probe = socket.socket(socket.AF_UNIX)
        try:
            probe.connect(str(path))
        except ConnectionRefusedError:
            path.unlink()
        else:
            raise RuntimeError("Selection bridge already running")
        finally:
            probe.close()
    server = socket.socket(socket.AF_UNIX)
    server.bind(str(path))
    os.chmod(path, 0o600)
    return path, server


def receive_request(connection):
    connection.settimeout(5)
    data = bytearray()
    while not data.endswith(b"\n") and len(data) <= 8 * 1024 * 1024:
        chunk = connection.recv(65536)
        if not chunk:
            break
        data.extend(chunk)
    request = json.loads(data)
    if not isinstance(request.get("lines"), list) or not all(isinstance(line, str) for line in request["lines"]):
        raise ValueError("Invalid menu choices")
    return request


def serve():
    path, server = bind_server()
    server.listen(4)
    selector = selectors.DefaultSelector()
    selector.register(server, selectors.EVENT_READ)
    selector.register(sys.stdin, selectors.EVENT_READ)
    client = None
    try:
        while True:
            for key, _ in selector.select():
                if key.fileobj is server:
                    connection, _ = server.accept()
                    try:
                        request = receive_request(connection)
                        if client:
                            connection.sendall(b'{"selection":null}\n')
                            connection.close()
                            continue
                        client = connection
                        print(json.dumps(request), flush=True)
                    except (ValueError, OSError):
                        connection.close()
                else:
                    line = sys.stdin.readline()
                    if not line:
                        return
                    if client:
                        try:
                            client.sendall(line.encode())
                        except OSError:
                            pass
                        client.close()
                        client = None
    finally:
        if client:
            client.close()
        server.close()
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    serve()
