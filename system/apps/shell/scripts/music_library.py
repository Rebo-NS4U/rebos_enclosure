#!/usr/bin/env python3
"""Local music index and MPRIS bridge. JSON lines in/out; no shell commands."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import re
import urllib.error
import urllib.parse
import urllib.request
import music_preview

AUDIO = {'.mp3', '.flac', '.ogg', '.opus', '.m4a', '.aac', '.wav', '.wma', '.aiff'}
LOCK = threading.Lock()


def emit(value):
    with LOCK:
        print(json.dumps(value), flush=True)


def lyrics_get(endpoint, params):
    request = urllib.request.Request('https://lrclib.net/api/' + endpoint + '?' +
        urllib.parse.urlencode(params), headers={
            'User-Agent': 'Enclosure Music v1 (https://github.com/Rebo-NS4U/rebos_enclosure)'})
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)

def lyrics_normal(value):
    return re.sub(r"[\W_]+", '', value.casefold())

def lyrics_primary(value):
    return re.split(r',|;| & | feat\.? | ft\.? ', value, flags=re.I)[0].strip()


class Library:
    def __init__(self, home=None):
        self.home = Path(home or Path.home())
        self.state_dir = Path(os.environ.get('XDG_STATE_HOME', self.home / '.local/state')) / 'enclosure/music'
        self.cache_dir = Path(os.environ.get('XDG_CACHE_HOME', self.home / '.cache')) / 'enclosure/music'
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state = self.read(self.state_dir / 'library.json', {})
        self.cache = self.read(self.cache_dir / 'index.json', {})
        from music_mixes import Mixes
        self.mixes = Mixes(self.state_dir / 'mixes.json', self.read, self.write)
        self.music = self.home / 'Music'
        config = Path(os.environ.get('XDG_CONFIG_HOME', self.home / '.config')) / 'user-dirs.dirs'
        if config.exists():
            for line in config.read_text().splitlines():
                if line.startswith('XDG_MUSIC_DIR='):
                    candidate = Path(line.split('=', 1)[1].strip('"').replace('$HOME', str(self.home)))
                    # xdg-user-dirs uses HOME to mean disabled, not the whole library.
                    if candidate != self.home:
                        self.music = candidate
        self.state.setdefault('folders', [str(self.music)])
        self.state.setdefault('favorites', [])
        self.state.setdefault('playlists', [])

    @staticmethod
    def read(path, fallback):
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            return fallback

    @staticmethod
    def write(path, value):
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(value, ensure_ascii=False))
        temp.replace(path)

    def inspect(self, path):
        stat = path.stat()
        key = str(path)
        # Lyrics and folder artwork may change while the audio file stays untouched.
        related = [path.with_suffix('.lrc')] + [path.parent / n for n in
                   ('cover.jpg', 'cover.png', 'folder.jpg', 'folder.png', 'front.jpg')]
        signature = [2, stat.st_mtime_ns, stat.st_size] + [
            [str(p), p.stat().st_mtime_ns, p.stat().st_size] for p in related if p.is_file()]
        if self.cache.get(key, {}).get('signature') == signature:
            return self.cache[key]['track']
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)],
                                capture_output=True, text=True, timeout=20)
        if result.returncode:
            raise ValueError('Unreadable audio: ' + str(path))
        data = json.loads(result.stdout)
        fmt = data.get('format', {})
        tags = {}
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                tags.update({k.lower(): v for k, v in stream.get('tags', {}).items()})
        tags.update({k.lower(): v for k, v in fmt.get('tags', {}).items()})
        art = self.artwork(path, data, signature)
        lyrics = next((v for k, v in tags.items() if k == 'lyrics' or k.startswith('lyrics-') or k.startswith('unsyncedlyrics')), '')
        sidecar = path.with_suffix('.lrc')
        if sidecar.exists():
            lyrics = sidecar.read_text(errors='replace')
        track = dict(path=key, url=path.as_uri(), title=tags.get('title') or path.stem,
                     artist=tags.get('artist') or 'Unknown artist', album=tags.get('album') or 'Unknown album',
                     duration=float(fmt.get('duration') or 0), art=art, lyrics=lyrics,
                     number=int(str(tags.get('track', '0')).split('/')[0]) if str(tags.get('track', '0')).split('/')[0].isdigit() else 0)
        if path.is_relative_to(self.music / 'Daily Mixes') and re.fullmatch(r'[A-Za-z0-9]{22}', path.stem):
            track['spotifyUri'] = 'spotify:track:' + path.stem
        self.cache[key] = dict(signature=signature, track=track)
        return track

    def artwork(self, path, data, signature):
        key = str(path)
        art = ''
        for name in ('cover.jpg', 'cover.png', 'folder.jpg', 'folder.png', 'front.jpg'):
            cover = path.parent / name
            if cover.exists():
                art = cover.as_uri()
                break
        if not art and any(s.get('disposition', {}).get('attached_pic') for s in data.get('streams', [])):
            cover = self.cache_dir / (hashlib.sha256((key + str(signature)).encode()).hexdigest() + '.jpg')
            if not cover.exists():
                subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-an', '-frames:v', '1', '-y', str(cover)],
                               capture_output=True, timeout=20)
            if cover.exists():
                art = cover.as_uri()
        return art

    def scan(self):
        paths = set()
        for folder in self.state['folders']:
            root = Path(folder).expanduser()
            if root.is_dir():
                paths.update(p.resolve() for p in root.rglob('*') if p.is_file() and p.suffix.lower() in AUDIO)
        tracks, errors = [], []
        for path in sorted(paths):
            try:
                tracks.append(self.inspect(path))
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                errors.append(str(error))
        self.write(self.cache_dir / 'index.json', self.cache)
        # Folder playlists are derived on every scan, so moved/deleted songs and
        # folders never leave stale saved playlists behind.
        folder_playlists = []
        if self.music.is_dir():
            folders = []
            for folder in self.music.iterdir():
                if not folder.is_dir():
                    continue
                # Daily Mixes is a container: each downloaded snapshot is its
                # own playlist. Ordinary library folders retain recursive songs.
                if folder.name == 'Daily Mixes':
                    folders.extend(child for child in folder.iterdir() if child.is_dir())
                else:
                    folders.append(folder)
            for folder in sorted(folders, key=lambda p: (p.name.casefold(), p.name)):
                root = folder.resolve()
                members = [t['path'] for t in tracks if Path(t['path']).is_relative_to(root)]
                if members:
                    folder_playlists.append(dict(
                        id='folder:' + hashlib.sha256(str(folder.absolute()).encode()).hexdigest(),
                        name=folder.name, paths=members, folder=True))
        state = dict(self.state, playlists=self.state['playlists'] + folder_playlists)
        return dict(tracks=tracks, state=state, errors=errors)

    def lyrics(self, track):
        if track.get('lyrics', '').strip():
            return dict(text=track['lyrics'], status='')
        title, artist = track.get('title', ''), track.get('artist', '')
        if not title or not artist or artist == 'Unknown artist':
            return dict(text='', status='Title and artist are needed to find lyrics.')
        album, duration = track.get('album', ''), float(track.get('duration') or 0)
        cache = self.cache_dir / ('lyrics-' + hashlib.sha256(
            json.dumps([title, artist, album, duration]).encode()).hexdigest() + '.json')
        cached = self.read(cache, None)
        if cached:
            return cached

        try:
            params = dict(track_name=title, artist_name=artist)
            if album and album != 'Unknown album':
                params['album_name'] = album
            if 1 <= duration <= 3600:
                params['duration'] = round(duration)
            try:
                data = lyrics_get('get', params)
            except urllib.error.HTTPError as error:
                if error.code not in (400, 404):
                    raise
                data = None
            if not data or not (data.get('syncedLyrics') or data.get('plainLyrics') or data.get('instrumental')):
                records = lyrics_get('search', dict(track_name=title, artist_name=lyrics_primary(artist)))
                matches = [r for r in records if lyrics_normal(r.get('trackName', '')) == lyrics_normal(title)
                    and lyrics_normal(lyrics_primary(r.get('artistName', ''))) == lyrics_normal(lyrics_primary(artist))
                    and (duration <= 0 or abs(float(r.get('duration') or 0) - duration) <= 5)]
                data = max(matches, key=lambda r: (bool(r.get('syncedLyrics')),
                    -abs(float(r.get('duration') or 0) - duration)), default=None)
            text = (data.get('syncedLyrics') or data.get('plainLyrics') or '') if data else ''
            result = dict(text=text, status='Instrumental — no lyrics.' if data and data.get('instrumental')
                          else '' if text else 'No lyrics found for this song.')
            if text or (data and data.get('instrumental')):
                self.write(cache, result)
            return result
        except (OSError, ValueError, TypeError, KeyError):
            return dict(text='', status='Lyrics unavailable. Try this song again when online.')

    def dispatch(self, cmd, args):
        media_actions = {
            "mixes_preview": lambda: music_preview.preview(args.get("uri")),
            "lyrics": lambda: self.lyrics(args.get("track") or {}),
        }
        if cmd in media_actions:
            return media_actions[cmd]()
        if cmd == 'mixes_download':
            data = self.mixes.dispatch('mixes_get', {})
            mix = next((m for m in data['current'] + data['saved']
                        if m['uri'] == args.get('uri') and m['version'] == args.get('version')), None)
            if not mix:
                raise ValueError('Mix changed; select it again before downloading')
            folder = self.music / 'Daily Mixes' / (mix['name'] + '-' + mix['version'][:12])
            if str(self.music) not in self.state['folders']:
                self.state['folders'].append(str(self.music))
                self.write(self.state_dir / 'library.json', self.state)
            return dict(folder=str(folder), links='https://open.spotify.com/playlist/' + mix['uri'].split(':')[-1])
        if cmd in ('mixes_get', 'mixes_save', 'mixes_refresh'):
            return self.mixes.dispatch(cmd, args)
        if cmd == 'scan':
            return self.scan()
        if cmd == 'save':
            for key in ('favorites', 'playlists'):
                if key in args:
                    self.state[key] = ([p for p in args[key] if not p.get('folder')]
                                       if key == 'playlists' else args[key])
            self.write(self.state_dir / 'library.json', self.state)
            return True
        if cmd == 'folder':
            result = subprocess.run(['zenity', '--file-selection', '--directory', '--title=Add music folder'],
                                    capture_output=True, text=True)
            if result.returncode:
                return None
            folder = result.stdout.strip()
            if folder and folder not in self.state['folders']:
                self.state['folders'].append(folder)
                self.write(self.state_dir / 'library.json', self.state)
            return self.scan()
        raise ValueError('Unknown music command: ' + cmd)


def start_mpris():
    """Expose local playback to the shell and hardware media keys."""
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
    DBusGMainLoop(set_as_default=True)
    iface = 'org.mpris.MediaPlayer2.Player'
    props = 'org.freedesktop.DBus.Properties'

    class Bridge(dbus.service.Object):
        def __init__(self):
            self.name = dbus.service.BusName('org.mpris.MediaPlayer2.enclosure_music', bus=dbus.SessionBus())
            super().__init__(self.name, '/org/mpris/MediaPlayer2')
            self.values = dict(PlaybackStatus='Stopped', LoopStatus='None', Rate=1.0, Shuffle=False,
                               Volume=0.8, Position=dbus.Int64(0), MinimumRate=1.0, MaximumRate=1.0,
                               CanGoNext=False, CanGoPrevious=False, CanPlay=False, CanPause=False,
                               CanSeek=False, CanControl=True, Metadata=dbus.Dictionary({}, signature='sv'))

        def action(self, action, **args):
            emit(dict(event='control', action=action, **args))

        @dbus.service.method(props, in_signature='s', out_signature='a{sv}')
        def GetAll(self, interface):
            if interface == iface:
                return self.values
            return dict(CanQuit=False, CanRaise=True, HasTrackList=False, Identity='Enclosure Music',
                        SupportedUriSchemes=dbus.Array(['file'], signature='s'),
                        SupportedMimeTypes=dbus.Array([], signature='s'))

        @dbus.service.method(props, in_signature='ss', out_signature='v')
        def Get(self, interface, name):
            return self.GetAll(interface)[name]

        @dbus.service.method(props, in_signature='ssv')
        def Set(self, interface, name, value):
            if interface == iface and name in ('Volume', 'Shuffle', 'LoopStatus'):
                self.action(name, value=float(value) if name == 'Volume' else bool(value) if name == 'Shuffle' else str(value))

        @dbus.service.signal(props, signature='sa{sv}as')
        def PropertiesChanged(self, interface, changed, invalidated):
            pass

        @dbus.service.signal(iface, signature='x')
        def Seeked(self, position):
            pass

        @dbus.service.method('org.mpris.MediaPlayer2')
        def Raise(self): self.action('Raise')
        @dbus.service.method(iface)
        def PlayPause(self): self.action('PlayPause')
        @dbus.service.method(iface)
        def Play(self): self.action('Play')
        @dbus.service.method(iface)
        def Pause(self): self.action('Pause')
        @dbus.service.method(iface)
        def Stop(self): self.action('Stop')
        @dbus.service.method(iface)
        def Next(self): self.action('Next')
        @dbus.service.method(iface)
        def Previous(self): self.action('Previous')
        @dbus.service.method(iface, in_signature='x')
        def Seek(self, offset): self.action('Seek', offset=int(offset))
        @dbus.service.method(iface, in_signature='ox')
        def SetPosition(self, track, position):
            if track == self.values['Metadata'].get('mpris:trackid'):
                self.action('SetPosition', position=int(position))

        def update(self, data):
            track = data.get('track') or {}
            metadata = dbus.Dictionary({
                'mpris:trackid': dbus.ObjectPath('/enclosure/track/' + hashlib.sha256(track.get('path', '').encode()).hexdigest()),
                'mpris:length': dbus.Int64(data.get('length', 0)), 'xesam:title': track.get('title', ''),
                'xesam:artist': dbus.Array([track.get('artist', '')], signature='s'),
                'xesam:album': track.get('album', ''), 'mpris:artUrl': track.get('art', ''),
                'xesam:url': track.get('url', ''), 'xesam:asText': track.get('lyrics', '')}, signature='sv')
            values = dict(PlaybackStatus=data['status'], Position=dbus.Int64(data['position']),
                          Volume=data['volume'], Shuffle=data['shuffle'], LoopStatus=data['loop'],
                          Metadata=metadata, CanGoNext=data['canNext'], CanGoPrevious=data['canPrevious'],
                          CanPlay=bool(track), CanPause=bool(track), CanSeek=bool(track))
            changed = {k: v for k, v in values.items() if k != 'Position' and self.values.get(k) != v}
            self.values.update(values)
            if changed:
                self.PropertiesChanged(iface, changed, [])
            if data.get('seeked'):
                self.Seeked(self.values['Position'])
            return False

    bridge = Bridge()
    threading.Thread(target=GLib.MainLoop().run, daemon=True).start()
    return lambda data: GLib.idle_add(bridge.update, data)


def main():
    library = Library()
    try:
        library.mixes.start()
    except OSError as error:
        print("Daily Mix bridge unavailable: " + str(error), file=sys.stderr)
    try:
        mpris = start_mpris()
    except Exception as error:
        print('Music MPRIS unavailable: ' + str(error), file=sys.stderr)
        mpris = lambda data: None
    # Disk work and file dialogs must not block playback updates or media keys.
    worker = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    lyric_worker = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def handle(request):
        try:
            data = library.dispatch(request['cmd'], request.get('args', {}))
            emit(dict(id=request['id'], ok=True, data=data))
        except Exception as error:
            emit(dict(id=request.get('id'), ok=False, error=str(error)))

    for line in sys.stdin:
        try:
            request = json.loads(line)
            if request['cmd'] == 'mpris':
                mpris(request['args'])
            else:
                (lyric_worker if request['cmd'] == 'lyrics' else worker).submit(handle, request)
        except (ValueError, KeyError) as error:
            print(str(error), file=sys.stderr)
    worker.shutdown(wait=False, cancel_futures=True)
    lyric_worker.shutdown(wait=False, cancel_futures=True)


if __name__ == '__main__':
    main()
