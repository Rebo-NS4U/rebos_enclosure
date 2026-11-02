"""Loopback byte-range relay; upstream URLs and headers remain in memory."""
import atexit
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.client import HTTPException
import ipaddress
import socket
import re
import threading
import time
from urllib.parse import urlparse, urlsplit, urlunsplit, quote, urljoin
from urllib.request import Request, HTTPRedirectHandler, HTTPCookieProcessor, build_opener
from http.cookiejar import CookieJar


class StreamRelay:
    def __init__(self, allow_local=False):
        self.allow_local = allow_local
        self.sources = OrderedDict()
        self.routes = {}
        self.lock = threading.Lock()
        self.next_id = 0
        self.failures = {}
        self.preloaded = OrderedDict()
        self.preload_hits = 0
        relay = self
        class Redirects(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                relay.validate(newurl)
                redirect = super().redirect_request(req, fp, code, msg, headers, newurl)
                if redirect and urlparse(req.full_url).hostname != urlparse(newurl).hostname:
                    redirect.remove_header('Cookie')
                    redirect.remove_header('Authorization')
                return redirect
        self.cookies = CookieJar()
        self.opener = build_opener(Redirects(), HTTPCookieProcessor(self.cookies))
        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            def log_message(self, *args):
                pass
            def do_HEAD(self):
                self.serve(False)
            def do_GET(self):
                self.serve(True)
            def serve_preloaded(self, body, source):
                with relay.lock:
                    entry = relay.preloaded.get(self.path)
                if entry is None or time.monotonic() - entry[0] >= 300:
                    return False
                _, data, total, metadata = entry
                requested = self.headers.get('Range')
                match = re.fullmatch(r'bytes=(\d+)-(\d*)', requested) if requested else None
                if requested and not match:
                    return False
                start = int(match[1]) if match else 0
                end = min(int(match[2]), total - 1) if match and match[2] else total - 1
                if start >= len(data) or end < start:
                    return False
                try:
                    self.send_response(206 if requested else 200)
                    for key, value in metadata.items():
                        self.send_header(key, value)
                    self.send_header('Content-Length', str(end - start + 1))
                    self.send_header('Accept-Ranges', 'bytes')
                    if requested:
                        self.send_header('Content-Range', f'bytes {start}-{end}/{total}')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    self.close_connection = True
                    if not body:
                        return True
                    self.wfile.write(data[start:min(end + 1, len(data))])
                    self.wfile.flush()
                    with relay.lock:
                        relay.preload_hits += 1
                    offset = len(data)
                    if offset <= end:
                        url, headers, _ = source
                        headers = dict(headers, Range=f'bytes={offset}-{end}', **{'Accept-Encoding': 'identity'})
                        if metadata.get('ETag'):
                            headers['If-Match'] = metadata['ETag']
                        with relay.opener.open(Request(url, headers=headers), timeout=20) as upstream:
                            relay.validate(upstream.url)
                            expected = f'bytes {offset}-{end}/{total}'
                            if upstream.status != 206 or upstream.headers.get('Content-Range') != expected:
                                raise ValueError('Preloaded range changed')
                            while offset <= end:
                                chunk = upstream.read(min(65536, end + 1 - offset))
                                if not chunk:
                                    raise OSError('Truncated video range')
                                self.wfile.write(chunk)
                                offset += len(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # Players routinely cancel a read when seeking.
                except (OSError, ValueError, HTTPException) as error:
                    # Headers have already been sent: never append an error page.
                    with relay.lock:
                        relay.preloaded.pop(self.path, None)
                    relay.failures[self.path] = str(getattr(error, 'code', type(error).__name__))
                    self.close_connection = True
                return True
            def serve(self, body):
                response_started = False
                with relay.lock:
                    source = relay.sources.get(self.path)
                if source is None:
                    self.send_error(404); return
                if self.serve_preloaded(body, source):
                    return
                url, headers, height = source
                headers = dict(headers)
                if self.headers.get('Range'):
                    headers['Range'] = self.headers['Range']
                headers['Accept-Encoding'] = 'identity'
                try:
                    with relay.opener.open(Request(url, headers=headers, method='GET' if body else 'HEAD'), timeout=20) as upstream:
                        relay.validate(upstream.url)
                        content_type = upstream.headers.get('Content-Type', '').lower()
                        prefix = upstream.read(64) if body else b''
                        playlist = body and (prefix.lstrip().startswith(b'#EXTM3U') or 'mpegurl' in content_type)
                        if playlist:
                            raw = prefix + upstream.read(2_000_000)
                            if len(raw) >= 2_000_000:
                                raise ValueError('Oversized playlist')
                            rewritten = relay.rewrite(raw.decode(), upstream.url, source[1], height).encode()
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                            self.send_header('Content-Length', str(len(rewritten)))
                            self.send_header('Connection', 'close')
                            self.end_headers()
                            response_started = True
                            self.close_connection = True
                            self.wfile.write(rewritten)
                            return
                        self.send_response(upstream.status)
                        for key in ('Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges', 'ETag', 'Last-Modified'):
                            if upstream.headers.get(key):
                                self.send_header(key, upstream.headers[key])
                        self.send_header('Connection', 'close')
                        self.end_headers()
                        response_started = True
                        self.close_connection = True
                        if body:
                            self.wfile.write(prefix)
                            while chunk := upstream.read(65536):
                                self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except (OSError, ValueError, HTTPException) as error:
                    relay.failures[self.path] = str(getattr(error, 'code', type(error).__name__))
                    self.close_connection = True
                    # Appending an HTTP error after media headers corrupts the
                    # video payload. Closing lets the player detect truncation.
                    if not response_started:
                        try: self.send_error(502, 'Video source unavailable')
                        except OSError: pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def preload(self, local, size=4 * 1024 * 1024):
        """Retain a bounded startup prefix for an already registered file."""
        parsed = urlsplit(local)
        if parsed.hostname != '127.0.0.1' or parsed.port != self.server.server_port:
            return False
        with self.lock:
            source = self.sources.get(parsed.path)
        if source is None:
            return False
        url, headers, _ = source
        size = min(max(1, size), 4 * 1024 * 1024)
        headers = dict(headers, Range=f'bytes=0-{size - 1}', **{'Accept-Encoding': 'identity'})
        with self.opener.open(Request(url, headers=headers), timeout=12) as upstream:
            self.validate(upstream.url)
            match = re.fullmatch(r'bytes 0-(\d+)/(\d+)', upstream.headers.get('Content-Range', ''))
            if upstream.status != 206 or not match or 'mpegurl' in upstream.headers.get('Content-Type', '').lower():
                return False
            count, total = int(match[1]) + 1, int(match[2])
            if count > size or count > total:
                return False
            data = upstream.read(count)
            if len(data) != count or data.lstrip().startswith(b'#EXTM3U'):
                return False
            metadata = {key: upstream.headers[key] for key in ('Content-Type', 'ETag', 'Last-Modified') if upstream.headers.get(key)}
        with self.lock:
            self.preloaded[parsed.path] = (time.monotonic(), data, total, metadata)
            self.preloaded.move_to_end(parsed.path)
            while len(self.preloaded) > 4:
                self.preloaded.popitem(last=False)
        return True

    def validate(self, url):
        parsed = urlparse(url)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Invalid media URL')
        if not self.allow_local:
            if parsed.scheme != 'https':
                raise ValueError('HTTPS media required')
            addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(entry[4][0]).is_global for entry in addresses):
                raise ValueError('Public video source required')

    def register(self, url, headers=None, height=None):
        parts = urlsplit(url)
        url = urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/%:@!$&'()*+,;=-._~"), quote(parts.query, safe="%=&+/:;?@!$'()*,~-._"), ''))
        self.validate(url)
        with self.lock:
            route_key = (url, tuple(sorted((headers or {}).items())), height)
            if route_key in self.routes:
                return self.routes[route_key]
            self.next_id += 1
            path = '/media/' + str(self.next_id)
            self.sources[path] = (url, {'User-Agent': 'Mozilla/5.0', **(headers or {})}, height)
            local = f'http://127.0.0.1:{self.server.server_port}{path}'
            self.routes[route_key] = local
        return local

    def rewrite(self, playlist, base, headers, height=None):
        def local(uri):
            if uri.startswith('data:'):
                return uri
            target = urljoin(base, uri)
            forwarded = headers if urlparse(target).hostname == urlparse(base).hostname else {key:value for key,value in headers.items() if key.lower() not in ('cookie','authorization')}
            return self.register(target, forwarded, height)
        raw = playlist.splitlines()
        variants = []
        for index, line in enumerate(raw):
            if line.startswith('#EXT-X-STREAM-INF') and index + 1 < len(raw):
                size = re.search(r'RESOLUTION=\d+x(\d+)', line)
                if size:
                    variants.append((int(size[1]), index))
        keep = None
        if variants and height is not None:
            eligible = [row for row in variants if row[0] <= height] if height else []
            keep = (max(eligible) if eligible else min(variants))[1]
        removed = {index for _, index in variants if keep is not None and index != keep}
        removed |= {index+1 for index in removed}
        lines = []
        for index, line in enumerate(raw):
            if index in removed:
                continue
            if line.startswith('#'):
                line = re.sub(r'URI="([^"]+)"', lambda match: 'URI="' + local(match[1]) + '"', line)
            elif line.strip():
                line = local(line.strip())
            lines.append(line)
        return '\n'.join(lines) + '\n'

    def close(self):
        self.server.shutdown()
        self.server.server_close()


_RELAY = None
_RELAY_LOCK = threading.Lock()


def register(url, headers=None, height=None):
    global _RELAY
    with _RELAY_LOCK:
        if _RELAY is None:
            _RELAY = StreamRelay()
            atexit.register(_RELAY.close)
        return _RELAY.register(url, headers, height)


def preload(local):
    return _RELAY.preload(local) if _RELAY is not None else False
