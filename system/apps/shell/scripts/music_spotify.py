"""Start Spotify only for explicit online Music actions, without raising a running app."""
import re
import shutil
import subprocess
import threading
import time

_lock = threading.Lock()


def running():
    try:
        result = subprocess.run(
            ['gdbus', 'call', '--session', '--dest', 'org.freedesktop.DBus',
             '--object-path', '/org/freedesktop/DBus', '--method',
             'org.freedesktop.DBus.NameHasOwner', 'org.mpris.MediaPlayer2.spotify'],
            check=True, capture_output=True, text=True, timeout=2)
        return result.stdout.strip() == '(true,)'
    except (OSError, subprocess.SubprocessError):
        return False


def hide_window():
    """Use Spotify's tray action; never close the player or affect another app."""
    def call(destination, path, method, *args):
        return subprocess.run(
            ['gdbus', 'call', '--session', '--dest', destination,
             '--object-path', path, '--method', method, '--', *args],
            check=True, capture_output=True, text=True, timeout=2).stdout

    try:
        items = call('org.kde.StatusNotifierWatcher', '/StatusNotifierWatcher',
                     'org.freedesktop.DBus.Properties.Get',
                     'org.kde.StatusNotifierWatcher', 'RegisteredStatusNotifierItems')
        for destination, path in re.findall(r"'([^'/]+)(/[^']*spotify[^']*)'", items):
            menu = call(destination, path, 'org.freedesktop.DBus.Properties.Get',
                        'org.kde.StatusNotifierItem', 'Menu')
            menu_path = re.search(r"objectpath '([^']+)'", menu)
            if not menu_path:
                continue
            path = menu_path[1]
            layout = call(destination, path, 'com.canonical.dbusmenu.GetLayout',
                          '0', '-1', '[]')
            # Invisible actions mean the window is already hidden. Never toggle it.
            for item_id, properties in re.findall(r"\((\d+), \{([^}]+)\}", layout):
                if ("'Minimize to Tray'" in properties
                        and "'visible': <false>" not in properties
                        and "'enabled': <false>" not in properties):
                    call(destination, path, 'com.canonical.dbusmenu.Event',
                         item_id, 'clicked', '<int32 0>', '0')
                    return True
        return False
    except (OSError, subprocess.SubprocessError):
        # A missing tray must not prevent playback or terminate Spotify.
        return False


def ensure_started():
    # Preview and playlist requests can arrive on separate worker threads.
    with _lock:
        if running():
            hide_window()
            return
        if shutil.which('spotify-launcher') and shutil.which('gtk-launch'):
            command = ['gtk-launch', 'spotify-launcher']
        elif shutil.which('spotify'):
            command = ['spotify']
        elif shutil.which('flatpak'):
            command = ['flatpak', 'run', 'com.spotify.Client']
        else:
            raise ValueError('Install Spotify and sign in to use Spotify features.')
        try:
            subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as error:
            raise ValueError('Spotify could not start. Open Spotify and try again.') from error
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if running():
                for _ in range(8):
                    if hide_window():
                        break
                    time.sleep(0.25)
                return
            time.sleep(0.25)
        raise ValueError('Spotify did not become ready. Open Spotify, sign in and try again.')
