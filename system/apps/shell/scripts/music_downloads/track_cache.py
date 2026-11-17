"""Short-lived public track metadata cache; playlists always resolve afresh."""
import functools
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

TTL = 6 * 60 * 60


def cached_track(fetch):
    @functools.wraps(fetch)
    def track(client, track_id, *args, **kwargs):
        identity = client.urlToId(track_id) if client.isUrl(track_id) else track_id
        key = hashlib.sha256(json.dumps([identity, bool(client.getIsrc), args, kwargs],
            sort_keys=True).encode()).hexdigest()
        folder = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'enclosure/music/tracks'
        path = folder / (key + '.json')
        try:
            if 0 <= time.time() - path.stat().st_mtime < TTL:
                value = json.loads(path.read_text())
                if isinstance(value, dict) and value:
                    return value
        except (OSError, ValueError):
            pass
        value = fetch(client, track_id, *args, **kwargs)
        if isinstance(value, dict) and value:
            temporary = None
            try:
                folder.mkdir(parents=True, exist_ok=True, mode=0o700)
                with tempfile.NamedTemporaryFile(mode='w', dir=folder, delete=False) as output:
                    temporary = Path(output.name)
                    json.dump(value, output)
                temporary.replace(path)
            except (OSError, ValueError):
                pass  # Cache failures must never prevent a download.
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        return value
    return track
