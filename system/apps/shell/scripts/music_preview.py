"""Preview Spotify tracks through the existing player, without library downloads."""
import json
import os
import re
import subprocess
import time

SPOTIFY_APPS = {'Spotify', 'spotify', 'com.spotify.Client'}


def focused_window():
    """Best effort: playback also works outside a Niri desktop session."""
    if not os.environ.get('NIRI_SOCKET'):
        return None
    try:
        result = subprocess.run(['niri', 'msg', '-j', 'focused-window'],
                                check=True, capture_output=True, text=True, timeout=1)
        window = json.loads(result.stdout)
        return window if isinstance(window, dict) and isinstance(window.get('id'), int) else None
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return None


def keep_background(previous):
    from music_spotify import hide_window
    # OpenUri can remap the client asynchronously. Hide it even when it does
    # not take focus, while preserving any application switch made by the user.
    restore_focus = bool(previous and previous.get('app_id') not in SPOTIFY_APPS)
    for _ in range(5):
        time.sleep(0.1)
        current = focused_window() if restore_focus else None
        hide_window()
        if not current:
            restore_focus = False
            continue
        if current['id'] == previous['id']:
            continue
        if current.get('app_id') in SPOTIFY_APPS:
            try:
                subprocess.run(['niri', 'msg', 'action', 'focus-window', '--id', str(previous['id'])],
                               check=True, capture_output=True, text=True, timeout=1)
            except (OSError, subprocess.SubprocessError):
                pass
        else:
            restore_focus = False


def preview(uri):
    if not isinstance(uri, str) or not re.fullmatch(r'spotify:track:[A-Za-z0-9]{22}', uri):
        raise ValueError('Choose a valid Spotify track to preview')
    from music_spotify import ensure_started
    ensure_started()
    previous = focused_window()
    try:
        subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.mpris.MediaPlayer2.spotify',
                        '--object-path', '/org/mpris/MediaPlayer2', '--method',
                        'org.mpris.MediaPlayer2.Player.OpenUri', uri],
                       check=True, capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError('Spotify preview unavailable. Open Spotify, sign in and try again. '
                         'No music was downloaded.') from error
    keep_background(previous)
    return {'uri': uri, 'status': 'Playing through Spotify in the background · no library download'}
