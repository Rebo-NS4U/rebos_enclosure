"""Browser authorization with a loopback callback and PKCE."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlparse


def browser_credentials(open_url, timeout=180, token_callback=None, client_id=None, redirect_uri=None):
    import requests
    from librespot.core import MercuryRequests
    from librespot.proto import Authentication_pb2 as Authentication

    client_id = client_id or MercuryRequests.keymaster_client_id
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    result = {}
    redirect = redirect_uri or "http://127.0.0.1:5588/login"
    callback_url = urlparse(redirect)
    if callback_url.scheme != "http" or callback_url.hostname != "127.0.0.1" or not callback_url.port or callback_url.query or callback_url.fragment:
        raise ValueError("Spotify redirect URI must be an HTTP loopback address with an explicit port.")

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            url = urlparse(self.path)
            query = parse_qs(url.query)
            valid = url.path == (callback_url.path or "/") and secrets.compare_digest(query.get("state", [""])[0], state)
            if valid:
                result.update(code=query.get("code", [""])[0], error=query.get("error", [""])[0])
            self.send_response(200 if valid else 400)
            self.end_headers()
            self.wfile.write(b"Return to Zotify Downloads to check your sign-in." if valid else b"Invalid sign-in callback.")

    try:
        callback_server = HTTPServer(("127.0.0.1", callback_url.port), Callback)
    except OSError as exc:
        if exc.errno == 98:
            raise RuntimeError("Another Spotify sign-in is already open. Complete or cancel that attempt before starting a new one.") from None
        raise
    with callback_server as server:
        server.timeout = 0.5
        open_url("https://accounts.spotify.com/authorize?" + urlencode({
            "response_type": "code", "client_id": client_id,
            "redirect_uri": redirect, "state": state,
            "code_challenge_method": "S256",
            "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("="),
            "scope": "streaming user-read-private user-read-email playlist-read-private user-library-read user-follow-read",
        }))
        deadline = time.monotonic() + timeout
        while not result and time.monotonic() < deadline:
            server.handle_request()
    if not result:
        raise RuntimeError("Browser sign-in timed out. Click Sign in with Spotify to retry.")
    if result.get("error") or not result.get("code"):
        raise RuntimeError("Spotify sign-in was declined. Please retry.")
    response = requests.post("https://accounts.spotify.com/api/token", data={
        "grant_type": "authorization_code", "client_id": client_id,
        "redirect_uri": redirect, "code": result["code"], "code_verifier": verifier,
    }, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"Spotify rejected browser sign-in (HTTP {response.status_code}).")
    token = dict(response.json(), client_id=client_id)
    if token_callback:
        token_callback(token)
    return Authentication.LoginCredentials(
        typ=Authentication.AuthenticationType.AUTHENTICATION_SPOTIFY_TOKEN,
        auth_data=token["access_token"].encode(),
    )
