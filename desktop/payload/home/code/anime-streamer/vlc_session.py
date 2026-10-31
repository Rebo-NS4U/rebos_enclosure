"""One native VLC window, private controls, and live subtitle rendering."""
import base64
import bisect
import json
import os
from pathlib import Path
import queue
import re
import secrets
import socket
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlencode, urlparse, unquote
from urllib.request import Request, build_opener, ProxyHandler
from gi.repository import GLib
import stream_relay
from vlc_theme import vlc_environment


INPUT_ERROR = re.compile(r'\bmain (?:input|stream) error:(?! INPUT_CONTROL_SET_POSITION 100\.0% failed)')


def read_cues(path):
    text = Path(path).read_text()
    result = []
    def seconds(value):
        h, m, s, ms = map(int, re.split('[:,.]', value))
        return h * 3600 + m * 60 + s + ms / 1000
    for block in re.split(r'\n\s*\n', text.strip()):
        match = re.search(r'(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)\s*\n(.*)', block, re.S)
        if match:
            result.append((seconds(match[1]), seconds(match[2]), match[3].strip()))
    return sorted(result)


class VlcSession:
    def __init__(self, settings, on_event, logpath, extra_args=()):
        self.on_event = on_event
        self.commands = queue.Queue()
        self.closed = threading.Event()
        self.loaded = False
        self.generation = 0
        self.requested = False
        self.finished = False
        self.stop_count = 0
        self.input_error = False
        self.pause_when_ready = False
        self.last = {}
        self.cues = []
        self.cue_starts = []
        self.caption_requested = False
        self.caption_registered = False
        self.anchor_id = None
        self.caption_text = None
        self.last_caption = 0
        self.last_state = {}
        self.start_volume = settings.get('volume', 80)
        self.directory = tempfile.TemporaryDirectory(prefix='media-vlc-')
        self.anchor = Path(self.directory.name) / 'Live English · local Whisper.srt'
        self.anchor.write_text('1\n00:00:00,000 --> 99:59:59,999\n\u2060\n')
        helper = Path.home() / '.local/share/vlc/lua/intf/media_browser.lua'
        helper.parent.mkdir(parents=True, exist_ok=True)
        script = Path(__file__).with_name('vlc_control.lua').read_bytes()
        if not helper.exists() or helper.read_bytes() != script:
            fd, temporary = tempfile.mkstemp(prefix='.media-browser-', dir=helper.parent)
            try:
                with os.fdopen(fd, 'wb') as output:
                    output.write(script)
                os.replace(temporary, helper)
            finally:
                Path(temporary).unlink(missing_ok=True)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        password = secrets.token_hex(24)
        self.endpoint = f'http://127.0.0.1:{port}/session.json'
        self.authorization = 'Basic ' + base64.b64encode((':' + password).encode()).decode()
        self.opener = build_opener(ProxyHandler({}))
        self.logpath = Path(logpath)
        self.logpath.parent.mkdir(parents=True, exist_ok=True)
        args = ['vlc', '--ignore-config', '--no-one-instance', '--no-media-library', '--no-loop', '--no-repeat',
                '--no-save-config', '--qt-continue=0', '--no-qt-video-autoresize',
                '--no-video-title-show', '--no-qt-privacy-ask', '--no-metadata-network-access', '--verbose=2',
                '--extraintf=luaintf:pause_click', '--lua-intf=media_browser',
                '--video-filter=pause_click', '--pause-click-mouse-button=1',
                '--pause-click-ignore-double-click',
                '--http-host=127.0.0.1', '--http-port=' + str(port),
                '--lua-config=media_browser={port=' + str(port) + ',password="' + password + '",fullscreen=' + str(bool(settings.get('fullscreen'))).lower() + '}',
                '--audio-language=eng,en', '--sub-language=eng,en', '--freetype-rel-fontsize=24']
        if settings.get('fullscreen'):
            args.append('--fullscreen')
        args.extend(extra_args)
        with self.logpath.open('w') as log:
            self.process = subprocess.Popen(args, stdout=log, stderr=log, env=vlc_environment())
        threading.Thread(target=self.monitor, daemon=True, name='vlc-player').start()

    def api(self, command=None, **values):
        if command:
            values['command'] = command
        url = self.endpoint + ('?' + urlencode(values) if values else '')
        request = Request(url, headers={'Authorization': self.authorization})
        with self.opener.open(request, timeout=3) as response:
            state = json.load(response)
        if state.get('ok') is False:
            raise RuntimeError('VLC could not apply the player command.')
        return state

    def emit(self, event):
        GLib.idle_add(self.on_event, event)

    def command(self, command):
        if not self.closed.is_set():
            self.commands.put(command)

    def load(self, links, title, paused=False):
        self.command(['load', links, title, paused])

    def public_stream(self, url, referer=''):
        if not url or not url.startswith('https://'):
            return url
        return stream_relay.register(url, {'Referer': referer} if referer else {})

    def subtitle_path(self, url, referer=''):
        if url.startswith('file://'):
            return unquote(urlparse(url).path)
        if not url.startswith(('https://', 'http://127.0.0.1:')):
            return url
        try:
            local = self.public_stream(url, referer)
            with self.opener.open(local, timeout=12) as response:
                data = response.read(2_000_001)
            if len(data) > 2_000_000:
                return ''
            extension = '.vtt' if data.lstrip().startswith(b'WEBVTT') else '.srt'
            path = Path(self.directory.name) / ('Provided English' + extension)
            path.write_bytes(data)
            if extension == '.vtt':
                converted = path.with_suffix('.srt')
                subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(path),
                                '-f', 'srt', str(converted)], check=True, capture_output=True, timeout=12)
                path = converted
            return str(path)
        except (OSError, subprocess.SubprocessError):
            return ''

    def clear_captions(self):
        self.command(['captions-clear'])

    def update_captions(self, path):
        self.command(['captions-file', path])

    def show_captions(self):
        self.command(['captions-show'])

    def apply(self, command):
        action = command[0]
        if action == 'load':
            links, title, paused = command[1:]
            video, referer, subtitle, audio = links
            options = ['no-start-paused', 'input-repeat=0', 'audio-language=eng,en', 'sub-language=eng,en']
            if referer:
                options.append('http-referrer=' + referer)
            if audio:
                options.extend(['demux=avformat', 'input-slave=' + self.public_stream(audio, referer)])
            if subtitle:
                path = self.subtitle_path(subtitle, referer)
                if path:
                    options.append('sub-file=' + path)
                    options.append('sub-description=Provided English')
            self.generation += 1
            self.loaded = self.finished = self.input_error = False
            self.caption_registered = self.caption_requested = False
            self.anchor_id = None
            self.cues, self.cue_starts = [], []
            self.last = {}
            self.requested = True
            self.pause_when_ready = paused
            self.log_offset = self.logpath.stat().st_size
            self.api('load', data=json.dumps(dict(url=self.public_stream(video, referer), title=title, options=options, generation=self.generation)))
        elif action == 'set_property' and command[1] == 'pause':
            self.api('pause', value='true' if command[2] else 'false')
        elif action == 'set_property' and command[1] == 'sid':
            self.api('subtitle', value=command[2])
        elif action == 'seek':
            self.api('seek', value=command[1])
        elif action == 'captions-file':
            self.cues = read_cues(command[1])
            self.cue_starts = [cue[0] for cue in self.cues]
        elif action == 'captions-show':
            self.caption_requested = True
            self.ensure_caption_track()
            if self.anchor_id is not None:
                self.api('subtitle', value=self.anchor_id)
        elif action == 'captions-clear':
            self.cues, self.cue_starts = [], []
            self.caption_requested = False
            self.api('clear-caption')
            if self.anchor_id is not None and self.last_state.get('sid') == self.anchor_id:
                self.api('subtitle', value=-1)
        elif action == 'observe_property':
            pass  # The native interface publishes the properties below.
        elif action in ('quit', 'stop'):
            self.requested = False
            if action == 'quit':
                self.close()
            else:
                self.api('stop')

    def ensure_caption_track(self):
        if self.loaded and not self.caption_registered:
            self.api('caption-register', value=str(self.anchor))
            self.caption_registered = True

    def poll(self, state):
        self.last_state = state
        if self.requested and (self.loaded or self.finished) and not state.get('eof') and state.get('state') == 'stopped':
            self.loaded = self.finished = False
            self.stop_count += 1
            self.emit({'event':'end-file', 'reason':'stop'})
            return
        if self.requested and state.get('eof') and not self.finished:
            # VLC also advances to the marker when demuxing fails. Only an
            # input that actually played to its end may advance the episode.
            duration = self.last.get('duration', 0)
            position = self.last.get('time-pos', 0)
            tolerance = min(10, max(2, duration * 0.01))
            if not self.loaded or (duration > 0 and position < duration - tolerance):
                self.input_error = True
            self.finished = True
            self.loaded = False
            if self.input_error:
                self.requested = False
                self.api('stop')
            self.emit({'event':'end-file', 'reason':'error' if self.input_error else 'eof'})
            return
        if not self.requested or self.finished or state.get('eof'):
            return
        if state.get('input_state') == 5:
            self.input_error = True
        if state.get('input') and state.get('input_state') in (2, 3) and not self.loaded:
            if self.pause_when_ready:
                self.api('pause', value='true')
                self.pause_when_ready = False
                state = dict(state, state='paused')
            self.loaded = True
            self.emit({'event':'file-loaded'})
        if not self.loaded:
            return
        if state.get('input_state') == 5:
            self.input_error = True
        anchor = state.get('anchor')
        if isinstance(anchor, int) and anchor >= 0:
            self.anchor_id = anchor
        values = {'time-pos':state.get('time',0), 'duration':state.get('duration',0), 'pause':state.get('state') == 'paused',
                  'sid':state.get('sid',-1) if state.get('sid',-1) >= 0 else False, 'sub-visibility':state.get('sid',-1) >= 0,
                  'whisper-captions': self.anchor_id is not None and state.get('sid') == self.anchor_id}
        for name, value in values.items():
            if self.last.get(name) != value:
                self.last[name] = value
                self.emit({'event':'property-change','name':name,'data':value})
        if self.caption_requested:
            self.ensure_caption_track()
        now = time.monotonic()
        text = ''
        if self.anchor_id is not None and state.get('sid') == self.anchor_id:
            position = state.get('time',0)
            index = bisect.bisect_right(self.cue_starts, position) - 1
            if 0 <= index < len(self.cues) and position < self.cues[index][1]:
                text = self.cues[index][2]
        if not text:
            if self.caption_text:
                self.api('clear-caption')
            self.caption_text = ''
        elif text != self.caption_text or now - self.last_caption > 1:
            self.api('caption', value=text)
            self.caption_text, self.last_caption = text, now

    def monitor(self):
        self.log_offset = 0
        try:
            for _ in range(100):
                if self.closed.is_set() or self.process.poll() is not None:
                    return
                try:
                    self.api()
                    break
                except OSError:
                    time.sleep(.05)
            else:
                raise RuntimeError('Could not connect to VLC.')
            self.api('volume', value=self.start_volume)
            poll_failures = 0
            while not self.closed.is_set() and self.process.poll() is None:
                while not self.commands.empty():
                    self.apply(self.commands.get_nowait())
                with self.logpath.open() as log:
                    log.seek(self.log_offset)
                    lines = log.read()
                    self.log_offset = log.tell()
                if INPUT_ERROR.search(lines):
                    self.input_error = True
                try:
                    state = self.api()
                except (OSError, ValueError):
                    poll_failures += 1
                    if poll_failures >= 3:
                        raise
                else:
                    poll_failures = 0
                    self.poll(state)
                self.closed.wait(.15)
        except (OSError, ValueError, RuntimeError) as error:
            self.last_error = type(error).__name__ + ': ' + str(error)
            if not self.closed.is_set() and self.process.poll() is None:
                self.emit({'event':'connection-error','error':'VLC could not complete the playback request.'})
                self.close()
        finally:
            self.process.wait()
            self.directory.cleanup()
            self.emit({'event':'process-exited','code':self.process.returncode,
                       'error': bool(getattr(self, 'last_error', None))})

    def close(self):
        self.closed.set()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
