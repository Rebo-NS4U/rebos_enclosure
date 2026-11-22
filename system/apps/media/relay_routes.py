"""Bound relay metadata by whole source families, preserving active owners."""
from collections import defaultdict, OrderedDict
from contextlib import contextmanager
import secrets
import time
from urllib.parse import urlsplit


class RelayRoutes:
    def __init__(self, relay):
        self.relay = relay
        self.groups = {}
        self.group_for = {}
        self.owners = defaultdict(set)
        self.leases = {}
        self.vod_segments = set()
        self.seek_segments = OrderedDict()

    def local_path(self, url):
        parts = urlsplit(url)
        if parts.hostname == '127.0.0.1' and parts.port == self.relay.server.server_port:
            return parts.path
        return None

    def _make_room(self, count, root, capacity):
        excess = len(self.relay.routes) + count - capacity
        protected = {group for groups in self.owners.values() for group in groups}
        protected.update(group for group, until in self.leases.items() if until > time.monotonic())
        protected.update(self.group_for.get(path) for path, entry in self.relay.preloaded.items()
                         if time.monotonic() - entry[0] < 300)
        protected.add(root)
        victims = []
        for group, members in self.groups.items():
            if excess <= 0:
                break
            if group not in protected:
                victims.append(group)
                excess -= len(members)
        if excess > 0:
            raise ValueError('Active media routes exceed relay capacity; retry after playback releases a source.')
        for group in victims:
            for path, key in self.groups.pop(group).items():
                self.group_for.pop(path, None)
                self.relay.routes.pop(key, None)
                self.relay.sources.pop(path, None)
                self.relay.failures.pop(path, None)
                self.relay.preloaded.pop(path, None)
                self.seek_segments.pop(path, None)
                self.vod_segments.discard(path)
            self.leases.pop(group, None)

    def register(self, entries, root, capacity):
        with self.relay.lock:
            if root is not None and root not in self.groups:
                raise ValueError('Media source expired; resolve it again.')
            keys = [(root, url, tuple(sorted(headers.items())), height) for url, headers, height in entries]
            pending = dict((key, source) for key, source in zip(keys, entries) if key not in self.relay.routes)
            self._make_room(len(pending), root, capacity)
            for key, source in pending.items():
                path = '/media/' + secrets.token_urlsafe(24)
                group = root or path
                self.groups.setdefault(group, {})[path] = key
                self.group_for[path] = group
                self.relay.sources[path] = source
                self.relay.routes[key] = f'http://127.0.0.1:{self.relay.server.server_port}{path}'
            return [self.relay.routes[key] for key in keys]

    @contextmanager
    def hold(self, path, owner):
        with self.relay.lock:
            group = self.group_for.get(path)
            if group:
                self.owners[owner].add(group)
                self.leases[group] = time.monotonic() + 30
        try:
            yield group
        finally:
            self.release(owner)

    def release(self, owner):
        with self.relay.lock:
            self.owners.pop(owner, None)

    def available(self, url):
        path = self.local_path(url)
        with self.relay.lock:
            return path is None or path in self.group_for

    @contextmanager
    def playback(self, owner, urls):
        with self.relay.lock:
            paths = [path for url in urls if (path := self.local_path(url)) is not None]
            if any(path not in self.group_for for path in paths):
                raise ValueError('Media source expired; resolve it again.')
            previous = self.owners[owner].copy()
            groups = {self.group_for[path] for path in paths}
            claimed = previous | groups
            self.owners[owner] = claimed
        try:
            yield
        except BaseException:
            with self.relay.lock:
                if self.owners.get(owner) is claimed:
                    if previous:
                        self.owners[owner] = previous
                    else:
                        self.owners.pop(owner, None)
            raise
        else:
            with self.relay.lock:
                if self.owners.get(owner) is claimed:
                    if groups:
                        self.owners[owner] = groups
                    else:
                        self.owners.pop(owner, None)
