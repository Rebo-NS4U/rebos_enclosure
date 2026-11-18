"""Start Spotify only for explicit online Music actions, without raising a running app."""
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


def ensure_started():
    # Preview and playlist requests can arrive on separate worker threads.
    with _lock:
        if running():
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
                return
            time.sleep(0.25)
        raise ValueError('Spotify did not become ready. Open Spotify, sign in and try again.')
