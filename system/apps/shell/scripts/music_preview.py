"""Preview Spotify tracks through the existing player, without library downloads."""
import re
import subprocess


def preview(uri):
    if not isinstance(uri, str) or not re.fullmatch(r'spotify:track:[A-Za-z0-9]{22}', uri):
        raise ValueError('Choose a valid Spotify track to preview')
    try:
        subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.mpris.MediaPlayer2.spotify',
                        '--object-path', '/org/mpris/MediaPlayer2', '--method',
                        'org.mpris.MediaPlayer2.Player.OpenUri', uri],
                       check=True, capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError('Spotify preview unavailable. Open Spotify, sign in and try again. '
                         'No music was downloaded.') from error
    return {'uri': uri, 'status': 'Preview opened in Spotify · no library download'}
