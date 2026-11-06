"""Explicit browser account connection; never export or persist browser cookies."""
import configparser
import json
import os
from pathlib import Path
import threading

CONFIG = Path.home() / '.config/anime-streamer/youtube-account.json'
LOCK = threading.RLock()
FEEDS = {}


def browsers():
    result = []
    for name, roots in (
        ('Zen', ['.config/zen', '.zen', '.var/app/app.zen_browser.zen/.zen']),
        ('Firefox', ['.mozilla/firefox', '.config/mozilla/firefox']),
    ):
        for relative in roots:
            root = Path.home() / relative
            ini = configparser.ConfigParser()
            ini.read(root / 'profiles.ini')
            for section in ini.sections():
                if not section.startswith('Profile') or not ini.has_option(section, 'Path'):
                    continue
                path = Path(ini[section]['Path'])
                if ini[section].get('IsRelative', '1') == '1':
                    path = root / path
                if (path / 'cookies.sqlite').is_file():
                    result.append(dict(id='firefox:' + str(path), label=name + ' · ' + ini[section].get('Name', section)))
    for name, browser, relative in (
        ('Chrome', 'chrome', '.config/google-chrome'),
        ('Chromium', 'chromium', '.config/chromium'),
        ('Brave', 'brave', '.config/BraveSoftware/Brave-Browser'),
    ):
        root = Path.home() / relative
        for path in sorted(root.glob('*')) if root.is_dir() else []:
            if (path / 'Cookies').is_file() or (path / 'Network/Cookies').is_file():
                result.append(dict(id=browser + ':' + str(path), label=name + ' · ' + path.name))
    return result


def selection():
    try:
        return json.loads(CONFIG.read_text()).get('browser', '')
    except (OSError, ValueError):
        return ''


def status():
    selected = selection()
    choices = browsers()
    match = next((row for row in choices if row['id'] == selected), None)
    return dict(connected=bool(match), browsers=choices, browser=selected if match else '',
                text=('Using ' + match['label'] + '. Refresh For You to check the current session.') if match else
                'Connect a browser profile signed in to YouTube. Videos and recommendations stay in this player.')


def assert_signed_in(browser):
    # Quiet extraction keeps cookie values and browser diagnostics out of UI/logs.
    from yt_dlp import YoutubeDL
    kind, profile = browser.split(':', 1)
    try:
        with YoutubeDL({'quiet': True, 'no_warnings': True, 'cookiesfrombrowser': (kind, profile),
                        'logger': QuietLogger()}) as ydl:
            signed_in = any(cookie.name in ('SAPISID', '__Secure-3PAPISID', '__Secure-1PAPISID')
                            and cookie.domain.lstrip('.') in ('youtube.com', 'www.youtube.com')
                            and not cookie.is_expired() for cookie in ydl.cookiejar)
    except Exception:
        raise ValueError('Could not read this browser session. Sign in to YouTube in that profile and retry.') from None
    if not signed_in:
        raise ValueError('This profile is not signed in to YouTube. Sign in in the browser, then press Finish connection.')


class QuietLogger:
    def debug(self, *args): pass
    def warning(self, *args): pass
    def error(self, *args): pass


def connect(browser, fetch):
    if browser not in {row['id'] for row in browsers()}:
        raise ValueError('Choose an available browser profile.')
    assert_signed_in(browser)
    # Verify the actual personalized feed before claiming the connection works.
    fetch(browser)
    with LOCK:
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(CONFIG, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as output:
            json.dump({'browser': browser}, output)
        FEEDS.clear()
    data = status()
    data['text'] = 'Connected. Your YouTube For You feed is ready in the player.'
    return data


def disconnect():
    with LOCK:
        CONFIG.unlink(missing_ok=True)
        FEEDS.clear()
    return status()
