"""Bound UI output independently of playback and other connected clients."""
import queue
import select
import socket
import threading
import time

MAX_FRAME = 1024 * 1024
SEND_TIMEOUT = 2


class ClientConnection:
    def __init__(self, connection):
        self.connection = connection
        self.pending = queue.Queue(maxsize=16)
        self.closed = threading.Event()
        self.worker = threading.Thread(target=self.write_pending, daemon=True)
        self.worker.start()

    def send(self, payload):
        if self.closed.is_set():
            return False
        try:
            if len(payload) > MAX_FRAME:
                raise queue.Full
            self.pending.put_nowait(payload)
        except queue.Full:
            self.close()
            return False
        return True

    def write_pending(self):
        try:
            while not self.closed.is_set():
                try:
                    payload = memoryview(self.pending.get(timeout=.1))
                except queue.Empty:
                    continue
                deadline = time.monotonic() + SEND_TIMEOUT
                while payload and not self.closed.is_set():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not select.select([], [self.connection], [], remaining)[1]:
                        return
                    try:
                        count = self.connection.send(payload, socket.MSG_DONTWAIT)
                    except BlockingIOError:
                        continue
                    if not count:
                        return
                    payload = payload[count:]
        except (OSError, ValueError):
            pass
        finally:
            self.close()

    def close(self):
        self.closed.set()
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.connection.close()
