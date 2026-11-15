"""Use browser-authorized tokens for Spotify Web API requests."""
import json
import os
from pathlib import Path
import tempfile
import time

import requests

TOKEN_FILE = Path.home() / '.config/zotify-gui/oauth.json'
CLIENT_FILE = Path.home() / '.config/zotify-gui/spotify-client.json'


def configured_client_id():
    from librespot.core import MercuryRequests
    try:
        return json.loads(CLIENT_FILE.read_text())['client_id']
    except (OSError, ValueError, KeyError):
        return MercuryRequests.keymaster_client_id


def configured_redirect_uri():
    try:
        return json.loads(CLIENT_FILE.read_text()).get('redirect_uri', 'http://127.0.0.1:5588/login')
    except (OSError, ValueError):
        return 'http://127.0.0.1:5588/login'


def authorized_client():
    try:
        data = json.loads(TOKEN_FILE.read_text())
        return data.get('client_id') == configured_client_id()
    except (OSError, ValueError):
        return False


def save_token(data, destination=None):
    destination = Path(destination or TOKEN_FILE)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stored = dict(data, expires_at=time.time() + data.get('expires_in', 3600))
    fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix='.oauth-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(stored, stream)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def access_token():
    from librespot.core import MercuryRequests
    try:
        data = json.loads(TOKEN_FILE.read_text())
    except (OSError, ValueError):
        raise RuntimeError('Sign in with Spotify again to authorize library access.') from None
    if data.get('client_id', MercuryRequests.keymaster_client_id) != configured_client_id():
        raise RuntimeError('Sign in with Spotify again to authorize your configured Developer app.')
    if data.get('expires_at', 0) > time.time() + 60:
        return data['access_token']
    response = requests.post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'refresh_token', 'refresh_token': data['refresh_token'],
        'client_id': data.get('client_id', MercuryRequests.keymaster_client_id),
    }, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f'Spotify could not refresh your login (HTTP {response.status_code}). Sign in with Spotify again.')
    updated = response.json()
    updated.setdefault('refresh_token', data['refresh_token'])
    updated['client_id'] = data.get('client_id', MercuryRequests.keymaster_client_id)
    save_token(updated)
    return updated['access_token']


def request_json(cls, url, params=None):
    response = requests.get(url, headers=cls.get_auth_header(), params=params, timeout=30)
    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f'Spotify returned an unreadable response (HTTP {response.status_code}).') from None
    if response.status_code >= 400 or isinstance(data, dict) and 'error' in data:
        status = response.status_code
        if status == 429:
            retry = response.headers.get('Retry-After')
            wait = f' Retry after {retry} seconds.' if retry and retry.isdigit() else ' Try again later.'
            raise RuntimeError('Spotify API rate limit exceeded (HTTP 429).' + wait)
        if status in (401, 403):
            raise RuntimeError(f'Spotify denied access (HTTP {status}). Sign in with Spotify again; access may be restricted by Spotify.')
        raise RuntimeError(f'Spotify API request failed (HTTP {status}).')
    if not isinstance(data, dict):
        raise RuntimeError('Spotify returned an unexpected response format.')
    return response.text, data


def install_api(cls):
    def headers(cls):
        return {'Authorization': 'Bearer ' + access_token(),
                'Accept-Language': str(cls.CONFIG.get_language()), 'Accept': 'application/json'}
    def headers_params(cls, limit, offset):
        return cls.get_auth_header(), {'limit': limit, 'offset': offset}
    def paged(cls, url, limit, offset, **kwargs):
        return request_json(cls, url, {'limit': limit, 'offset': offset, **kwargs})[1]
    cls.get_auth_header = classmethod(headers)
    cls.get_auth_header_and_params = classmethod(headers_params)
    cls.invoke_url_with_params = classmethod(paged)
    cls.invoke_url = classmethod(lambda cls, url, tryCount=0: request_json(cls, url))
