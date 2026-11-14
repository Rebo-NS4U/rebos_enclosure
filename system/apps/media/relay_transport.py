"""Connect HTTPS relay requests to checked numeric addresses, retaining TLS identity."""
from http.client import HTTPSConnection
import ipaddress
import socket
from urllib.request import HTTPSHandler


def public_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    answers = socket.getaddrinfo(*address, type=socket.SOCK_STREAM)
    if not answers or any(not ipaddress.ip_address(answer[4][0]).is_global for answer in answers):
        raise ValueError('Public video source required')
    last_error = None
    for family, kind, protocol, _, destination in answers:
        connection = socket.socket(family, kind, protocol)
        try:
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                connection.settimeout(timeout)
            if source_address:
                connection.bind(source_address)
            # Use this exact checked sockaddr; create_connection would resolve again.
            connection.connect(destination)
            return connection
        except OSError as error:
            connection.close()
            last_error = error
    raise last_error


class PublicHTTPSConnection(HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = public_connection


class PublicHTTPSHandler(HTTPSHandler):
    def https_open(self, request):
        return self.do_open(PublicHTTPSConnection, request, context=self._context)
