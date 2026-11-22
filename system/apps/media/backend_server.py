#!/usr/bin/env python3
"""On-demand user service; active playback survives UI disconnections."""
import json
import os
from pathlib import Path
import signal
import socket
import threading
import time
import uuid
from gi.repository import GLib
import menu_backend as backend
import torbox_source
import youtube_account
from client_connection import ClientConnection, MAX_FRAME
from runtime_socket import prepare_socket, socket_identity, unlink_socket


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
        self.idle_since = None

    def send(self, message):
        payload = (json.dumps(message) + '\n').encode()
        with self.lock:
            if message.get('event') in ['playback', 'captions', 'paused', 'episode', 'subtitle-state', 'subtitle-tracks', 'next-episode', 'download', 'seek-preview', 'skip-intro']:
                self.latest[message['event']] = message
            target = message.get('client')
            clients = [(target, self.clients[target])] if target in self.clients else [] if target else list(self.clients.items())
            for key, client in clients:
                if not client.send(payload):
                    self.clients.pop(key, None)

    def ready(self):
        engine = backend.engine
        return dict(event='ready', settings=engine.settings, filterOptions=backend.app.filter_fields(), mediaGenres=backend.media_sources.discovery_catalogue.GENRES,
                    youtubeRecommendations=backend.media_sources.YOUTUBE_RECOMMENDATIONS,
                    torbox=torbox_source.status(), youtubeAccount=youtube_account.status(),
                    playerPid=engine.player.pid if engine.player is not None and engine.player.poll() is None else None)

    def read_client(self, key, client):
        try:
            with client.connection.makefile('rb') as stream:
                while line := stream.readline(MAX_FRAME + 1):
                    if len(line) > MAX_FRAME:
                        break
                    try:
                        request = json.loads(line)
                        if not isinstance(request, dict):
                            raise ValueError('Invalid request')
                        request['_client'] = key
                        GLib.idle_add(backend.dispatch, request)
                    except ValueError:
                        self.send(dict(event='error', text='Invalid request', client=key))
        except (OSError, UnicodeError):
            pass
        finally:
            client.close()
            with self.lock:
                self.clients.pop(key, None)

    def accept_clients(self):
        while True:
            try:
                connection, _ = self.listener.accept()
            except OSError:
                return
            key = uuid.uuid4().hex
            with self.lock:
                if len(self.clients) >= 16:
                    connection.close()
                    continue
                client = ClientConnection(connection)
                self.clients[key] = client
                for message in [self.ready()] + list(self.latest.values()):
                    client.send((json.dumps(message) + '\n').encode())
            threading.Thread(target=self.read_client, args=(key, client), daemon=True).start()

    def check_idle(self):
        # Keep paused players and players still preparing a stream alive too.
        with self.lock:
            player = backend.engine.player
            if self.clients or backend.engine.download_active or (player is not None and player.poll() is None):
                self.idle_since = None
            elif self.idle_since is None:
                self.idle_since = time.monotonic()
            elif time.monotonic() - self.idle_since >= 5:
                self.loop.quit()
        return True

    def run(self):
        prepare_socket(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.listener = socket.socket(socket.AF_UNIX)
        self.listener.bind(str(self.path))
        identity = socket_identity(self.path)
        self.path.chmod(0o600)
        self.listener.listen(8)
        backend.engine = backend.Engine()
        backend.send = self.send
        signal.signal(signal.SIGTERM, lambda *_: self.loop.quit())
        threading.Thread(target=self.accept_clients, daemon=True).start()
        idle_timer = GLib.timeout_add_seconds(1, self.check_idle)
        try:
            self.loop.run()
        finally:
            GLib.source_remove(idle_timer)
            backend.engine.stop()
            self.listener.close()
            with self.lock:
                for client in self.clients.values():
                    client.close()
                self.clients.clear()
            unlink_socket(self.path, identity)
            backend.app.POOL.shutdown(wait=False, cancel_futures=True)


if __name__ == '__main__':
    BackendServer().run()
