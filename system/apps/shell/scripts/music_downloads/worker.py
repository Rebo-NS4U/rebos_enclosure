"""Run Zotify with browser authorization, never a password prompt."""
import json
import os
from pathlib import Path
import sys
import tempfile


def create_browser_session(session_type, location, browser_credentials):
    fd, temporary = tempfile.mkstemp(dir=location.parent, prefix=".login-")
    os.close(fd)
    try:
        credentials = browser_credentials(lambda url: print("LOGIN_URL " + url, flush=True))
        conf = session_type.Configuration.Builder().set_stored_credential_file(temporary).build()
        builder = session_type.Builder(conf)
        builder.login_credentials = credentials
        session = builder.create()
        os.chmod(temporary, 0o600)
        os.replace(temporary, location)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return session


def browser_login(cls, args, login_only=False):
    from librespot.core import Session
    from zotify.config import Config
    from auth import browser_credentials

    from api import authorized_client, configured_client_id, configured_redirect_uri, save_token

    location = Path(Config.get_credentials_location())
    cls.SESSION = None
    if location.is_file():
        try:
            conf = Session.Configuration.Builder().set_store_credentials(False).build()
            cls.SESSION = Session.Builder(conf).stored_file(str(location)).create()
        except RuntimeError:
            print("Saved playback login expired. Sign in through your browser.", flush=True)
    if cls.SESSION is None:
        cls.SESSION = create_browser_session(Session, location, browser_credentials)
    try:
        if login_only or not authorized_client():
            print("Authorize library access with your Spotify Developer app in the browser.", flush=True)
            browser_credentials(lambda url: print("LOGIN_URL " + url, flush=True),
                                client_id=configured_client_id(), redirect_uri=configured_redirect_uri(), token_callback=save_token)
        print("Signed in to Spotify.", flush=True)
    except BaseException:
        cls.SESSION.close()
        raise
    if login_only:
        cls.SESSION.close()
        raise SystemExit(0)


def run():
    payload = json.loads(sys.stdin.readline())
    from zotify.zotify import Zotify
    from zotify.__main__ import main
    from api import install_api
    install_api(Zotify)
    Zotify.login = classmethod(lambda cls, args: browser_login(cls, args, payload.get("login_only", False)))
    sys.argv = ["zotify", *payload["args"]]
    main()


if __name__ == "__main__":
    os.umask(0o077)
    try:
        run()
    except Exception as exc:
        print(f"Zotify failed: {exc}", flush=True)
        sys.exit(1)
