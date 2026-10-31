#!/usr/bin/env python3
"""Persistent user service; UI connections never own playback's lifetime."""
import json
import os
from pathlib import Path
import signal
import socket
import threading
import uuid
from gi.repository import GLib
import menu_backend as backend


def socket_path():
    return Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp')) / f'anime-streamer-{os.getuid()}.sock'


class BackendServer:
    def __init__(self, path=None):
        self.path = Path(path) if path else socket_path()
        self.clients = {}
        self.latest = {}
        self.lock = threading.RLock()
        self.loop = GLib.MainLoop()
        self.listener = None

    def send(self, message):
        payload = (json.dumps(message) + '\n').encode()
        with self.lock:
            if message.get('event') in ['playback', 'captions', 'paused', 'episode', 'subtitle-state']:
                self.latest[message['event']] = message
            target = message.get('client')
            clients = [(target, self.clients[target])] if target in self.clients else [] if target else list(self.clients.items())
            for key, connection in clients:
                try:
                    connection.sendall(payload)
                except OSError:
                    self.clients.pop(key, None)

    def ready(self):
        engine = backend.engine
        return dict(event='ready', settings=engine.settings, filterOptions=backend.app.filter_fields(), mediaGenres=backend.media_sources.discovery_catalogue.GENRES,
                    youtubeRecommendations=backend.media_sources.YOUTUBE_RECOMMENDATIONS,
                    torbox=backend.torbox_source.status(),
                    playerPid=engine.player.pid if engine.player is not None and engine.player.poll() is None else None)

    def read_client(self, key, connection):
        try:
            with connection, connection.makefile('r') as stream:
                for line in stream:
                    try:
                        request = json.loads(line)
                        if not isinstance(request, dict):
                            raise ValueError('Invalid request')
                        request['_client'] = key
                        GLib.idle_add(backend.dispatch, request)
                    except ValueError:
                        self.send(dict(event='error', text='Invalid request', client=key))
        except OSError:
            pass
        finally:
            with self.lock:
                self.clients.pop(key, None)

    def accept_clients(self):
        while True:
            try:
                connection, _ = self.listener.accept()
            except OSError:
                return
            key = uuid.uuid4().hex
            # Connections are user-local and continuously read by menu_client.
            with self.lock:
                self.clients[key] = connection
                try:
                    messages = [self.ready()] + list(self.latest.values())
                    connection.sendall(''.join(json.dumps(message) + '\n' for message in messages).encode())
                except OSError:
                    self.clients.pop(key, None)
                    connection.close()
                    continue
            threading.Thread(target=self.read_client, args=(key, connection), daemon=True).start()

    def run(self):
        if self.path.exists():
            with socket.socket(socket.AF_UNIX) as probe:
                try:
                    probe.connect(str(self.path))
                except OSError:
                    self.path.unlink(missing_ok=True)
                else:
                    raise RuntimeError('Anime service is already running')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.listener = socket.socket(socket.AF_UNIX)
        self.listener.bind(str(self.path))
        self.path.chmod(0o600)
        self.listener.listen(8)
        backend.engine = backend.Engine()
        backend.send = self.send
        signal.signal(signal.SIGTERM, lambda *_: self.loop.quit())
        threading.Thread(target=self.accept_clients, daemon=True).start()
        try:
            self.loop.run()
        finally:
            backend.engine.stop()
            self.listener.close()
            with self.lock:
                for connection in self.clients.values():
                    try:
                        connection.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    connection.close()
                self.clients.clear()
            self.path.unlink(missing_ok=True)
            backend.app.POOL.shutdown(wait=False, cancel_futures=True)


if __name__ == '__main__':
    BackendServer().run()
