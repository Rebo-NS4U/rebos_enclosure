"""One native VLC window, private controls, and live subtitle rendering."""
import base64
import bisect
from functools import lru_cache
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


# VLC logs rejected seeks and recoverable clock adjustments as input errors.
INPUT_ERROR = re.compile(
    r'\bmain (?:input|stream) error:(?!\s*(?:INPUT_CONTROL_SET_(?:POSITION|TIME)\b|ES_OUT_SET_\(GROUP_\)PCR\b))'
)


@lru_cache(maxsize=1)
def pause_click_available():
    """Never pass plugin-only options unless this VLC can parse them."""
    try:
        result = subprocess.run(['vlc', '-p', 'pause_click', '--advanced', '--help-verbose'],
                                capture_output=True, text=True, timeout=5)
        return result.returncode == 0 and '--pause-click-mouse-button' in result.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def read_cues(path):
    data = Path(path).read_bytes()
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        text = data.decode('utf-16')
    else:
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            from charset_normalizer import from_bytes
            match = from_bytes(data).best()
            if match is None or match.chaos > .1:
                raise ValueError('Subtitle encoding is uncertain')
            text = str(match)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    result = []
    def seconds(value):
        h, m, s, ms = map(int, re.split('[:,.]', value))
        return h * 3600 + m * 60 + s + ms / 1000
    for block in re.split(r'\n\s*\n', text.strip()):
        match = re.search(r'(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)\s*\n(.*)', block, re.S)
        if match:
            result.append((seconds(match[1]), seconds(match[2]), match[3].strip()))
    return sorted(result)


# Quality exception: Independent rejection guard clauses keep invalid captions and stale process actions fail-closed.
# Numeric ceilings are enforced by desktop/scripts/quality.py.
def provided_cues_usable(cues, duration=0):  # pylint: disable=too-many-return-statements
    """Conservative structural checks; these cannot judge translation accuracy."""
    if len(cues) < 10:
        return False
    texts = [re.sub(r'<[^>]*>|\\{[^}]*}', '', text).strip() for _, _, text in cues]
    if any(not text or '\ufffd' in text or len(text) > 500 for text in texts):
        return False
    # English is the player's subtitle output language, including when Whisper
    # detects Spanish/other source audio. Require positive evidence in dialogue;
    # a provider's language label alone is not reliable. Uncertain files fall back.
    words = re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)?", ' '.join(texts).casefold())
    common = set("the a an and or but if then because so of to in on at for from with as is are was were be been being i you he she it we they me him her us them my your his our their this that these those what who when where why how not no yes do does did have has had can could will would should must don't i'm it's you're that's i'll can't just know think want go come get let please okay thank thanks about here there now really all some up out good right well".split())
    hits = [word for word in words if word in common]
    if not words or len(hits) / len(words) < .15 or len(set(hits)) < 8:
        return False
    if any(start < 0 or not 0.15 <= end - start <= 20 for start, end, _ in cues):
        return False
    if len(set(texts)) < len(texts) * .35:
        return False
    if sum(end - start for start, end, _ in cues) < 30:
        return False
    if duration > 0:
        if cues[-1][1] > duration + 15 or cues[-1][1] < duration * .65:
            return False
        if len(cues) < duration / 20:
            return False
    return True


# Quality exception: One owner controls this process/session lifetime; explicit state fields preserve existing transition invariants.
# Numeric ceilings are enforced by desktop/scripts/quality.py.
class VlcSession:  # pylint: disable=too-many-instance-attributes
    # Quality exception: Distinct inputs and intermediate results are explicit within this bounded operation; retain readable names over count-driven packing.
    # Numeric ceilings are enforced by desktop/scripts/quality.py.
    def __init__(self, settings, on_event, logpath, extra_args=()):  # pylint: disable=too-many-statements
        self.on_event = on_event
        self.commands = queue.Queue()
        self.closed = threading.Event()
        self.loaded = False
        self.generation = 0
        self.subtitle_revision = 0  # A nonzero revision records a manual choice for this input.
        self.pending_subtitle = None
        self.requested = False
        self.finished = False
        self.stop_count = 0
        self.input_error = False
        self.pause_when_ready = False
        self.last = {}
        self.cues = []
        self.cue_starts = []
        self.caption_requested = False
        self.provided_cues = []
        self.whisper_cues = []
        self.subtitle_source = 'off'
        self.caption_error = ''
        self.live_enabled = settings.get('live_subtitles', True)
        self.validate_provider = True
        self.subtitle_loading = False
        self.caption_text = None
        self.last_caption = 0
        self.last_state = {}
        self.start_volume = settings.get('volume', 80)
        self.audio_normalization = bool(settings.get('audio_normalization', True))
        self.directory = tempfile.TemporaryDirectory(prefix='media-vlc-')
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
                '--qt-continue=0', '--no-qt-video-autoresize',
                '--no-video-title-show', '--osd', '--no-qt-privacy-ask', '--no-metadata-network-access', '--verbose=2',
                '--extraintf=luaintf', '--lua-intf=media_browser',
                '--http-host=127.0.0.1', '--http-port=' + str(port),
                '--lua-config=media_browser={port=' + str(port) + ',password="' + password + '",fullscreen=' + str(bool(settings.get('fullscreen'))).lower() + '}',
                '--audio-language=eng,en', '--sub-language=eng,en', '--freetype-font=' + settings.get('subtitle_font', 'OpenDyslexic'), '--freetype-rel-fontsize=24']
        if settings.get('fullscreen'):
            args.append('--fullscreen')
        if self.audio_normalization:
            # Strong dialogue leveling: compress above -24 dB, then restore 6 dB.
            args.extend(['--compressor-threshold=-24', '--compressor-ratio=8',
                         '--compressor-attack=5', '--compressor-release=250',
                         '--compressor-knee=6', '--compressor-makeup-gain=6'])
        if pause_click_available():
            args[args.index('--extraintf=luaintf')] = '--extraintf=luaintf:pause_click'
            args.extend(['--video-filter=pause_click', '--pause-click-mouse-button=1',
                         '--pause-click-ignore-double-click'])
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

    def load(self, links, title, paused=False, validate_provider=True, *, subtitle_choice=None):
        self.command(['load', links, title, paused, validate_provider, subtitle_choice])

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
            path = Path(self.directory.name) / ('Provided English-' + secrets.token_hex(8) + extension)
            path.write_bytes(data)
            if extension == '.vtt':
                converted = path.with_suffix('.srt')
                subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(path),
                                '-f', 'srt', str(converted)], check=True, capture_output=True, timeout=12)
                path = converted
            return str(path)
        except (OSError, ValueError, subprocess.SubprocessError):
            return ''

    def clear_captions(self):
        self.command(['captions-clear'])

    def update_captions(self, path):
        self.command(['captions-file', path])

    def show_captions(self):
        self.command(['captions-show'])

    def subtitle_tracks(self):
        state = self.last_state
        options = [dict(id='off', label='Off')]
        if self.provided_cues:
            options.append(dict(id='provided', label='Provided English · checked'))
        options.append(dict(id='whisper', label='Whisper English · local AI'))
        options.extend(dict(id=f"native:{track['id']}", label='Video English · ' + str(track['name']))
                       for track in self.english_tracks(state))
        source = self.subtitle_source
        if source not in {row['id'] for row in options}:
            source = 'off'
        return dict(selected=source, options=options, available=bool(self.loaded),
                    generating=source == 'whisper' and not self.whisper_cues,
                    failed=source == 'whisper' and bool(getattr(self, 'caption_error', '')))

    def select_subtitle_source(self, source):
        if source not in {row['id'] for row in self.subtitle_tracks()['options']}:
            return
        self.subtitle_revision += 1
        self.api('clear-caption')
        self.caption_text = ''
        self.set_caption_source(source)
        if source.startswith('native:'):
            self.api('subtitle', value=int(source.split(':')[1]))
        else:
            self.api('subtitle', value=-1)

    @staticmethod
    def english_tracks(state):
        return [track for track in state.get('subtitles', [])
                if track.get('id', -1) >= 0 and re.search(r'\b(english|eng|en)\b', str(track.get('name', '')), re.I)]

    def set_caption_source(self, source):
        self.subtitle_source = source
        self.caption_requested = source in ('provided', 'whisper')
        self.cues = self.provided_cues if source == 'provided' else self.whisper_cues if source == 'whisper' else []
        self.cue_starts = [cue[0] for cue in self.cues]

    def apply_pending_subtitle(self):
        if not self.loaded or self.pending_subtitle is None:
            return
        _, generation, revision, path, cues = self.pending_subtitle
        self.pending_subtitle = None
        if generation != self.generation:
            return
        self.subtitle_loading = False
        if self.validate_provider:
            if provided_cues_usable(cues, self.last_state.get('duration', 0)):
                self.provided_cues = cues
        elif path:
            try:
                self.api('addsubtitle', value=path, select='true' if revision == self.subtitle_revision else 'false')
            except (OSError, ValueError, RuntimeError):
                pass  # An optional subtitle failure must not stop the video.

    def apply(self, command):
        handler = self.COMMAND_HANDLERS.get(command[0])
        if handler is not None:
            getattr(self, handler)(command)

    COMMAND_HANDLERS = {'load': '_command_load', 'subtitle-ready': '_command_subtitle_ready', 'subtitle-source': '_command_subtitle_source', 'seek': '_command_seek', 'captions-file': '_command_captions_file', 'captions-show': '_command_captions_show', 'captions-clear': '_command_captions_clear', 'observe_property': '_command_observe_property', 'quit': '_command_quit', 'stop': '_command_quit', 'set_property': '_command_property'}

    def input_options(self, links):
        video, referer, _subtitle, audio = links
        options = ['no-start-paused', 'input-repeat=0', 'audio-language=eng,en', 'sub-language=eng,en']
        if video.startswith(('https://', 'http://')):
            options.extend(['network-caching=' + ('1500' if self.validate_provider else '500'), 'prefetch-buffer-size=65536'])
            if str(getattr(links, 'format_name', '')).startswith('mov,'):
                options.append('demux=avformat')
        if self.audio_normalization:
            options.append('audio-filter=compressor')
        if referer:
            options.append('http-referrer=' + referer)
        if audio:
            options.extend(['demux=avformat', 'input-slave=' + self.public_stream(audio, referer)])
        return options

    def prepare_subtitle(self, subtitle, referer):
        generation, revision, validate_provider = self.generation, self.subtitle_revision, self.validate_provider
        def prepare_subtitle():
            path, cues = '', []
            try:
                path = self.subtitle_path(subtitle, referer)
                if path and validate_provider:
                    cues = read_cues(path)
            except (OSError, ValueError, ImportError):
                pass  # Captions must never delay or prevent playback.
            self.command(['subtitle-ready', generation, revision, path, cues])
        threading.Thread(target=prepare_subtitle, daemon=True, name='media-subtitle').start()


    def _command_load(self, command):
        links, title, paused, self.validate_provider, self.subtitle_choice = command[1:]
        video, referer, subtitle, audio = links
        options = self.input_options(links)
        self.provided_cues = []
        self.whisper_cues = []
        self.caption_error = ''
        self.generation += 1
        self.pending_subtitle = None
        self.subtitle_revision = 0
        self.subtitle_loading = bool(subtitle)
        self.loaded = self.finished = self.input_error = False
        self.set_caption_source('off')
        self.last = {}
        self.last_state = {}
        self.requested = True
        self.pause_when_ready = paused
        self.log_offset = self.logpath.stat().st_size
        local = self.public_stream(video, referer)
        sources = [local] + [option.partition('=')[2] for option in options if option.startswith('input-slave=')]
        with stream_relay.playback(self, sources):
            self.api('load', data=json.dumps(dict(url=local, title=title, options=options, generation=self.generation, whisper_only=False)))
        if subtitle:
            self.prepare_subtitle(subtitle, referer)

    def _command_subtitle_ready(self, command):
        if command[1] == self.generation and self.requested and not self.finished:
            self.pending_subtitle = command
            self.apply_pending_subtitle()


    def _command_subtitle_source(self, command):
        self.subtitle_choice = None
        self.select_subtitle_source(command[1])


    def _command_seek(self, command):
        try:
            self.api('seek', value=command[1])
        except RuntimeError:
            self.emit({'event': 'command-error', 'error': 'VLC could not seek in this stream.'})


    def _command_captions_file(self, command):
        self.whisper_cues = read_cues(command[1])
        if self.subtitle_source == 'whisper':
            self.cues = self.whisper_cues
            self.cue_starts = [cue[0] for cue in self.cues]


    def _command_captions_show(self, command):
        self.caption_requested = self.subtitle_source in ('provided', 'whisper')


    def _command_captions_clear(self, command):
        self.whisper_cues = []
        if self.subtitle_source != 'provided':
            self.cues, self.cue_starts = [], []
            self.caption_requested = False
            self.caption_text = ''
            self.api('clear-caption')


    def _command_observe_property(self, command):
        pass  # The native interface publishes the properties below.


    def _command_quit(self, command):
        action = command[0]
        self.requested = False
        if action == 'quit':
            self.close()
        else:
            self.api('stop')


    def _command_property(self, command):
        if command[1] == "pause":
            self.api('pause', value='true' if command[2] else 'false')
        elif command[1] == "sid":
            self._command_subtitle_source(['subtitle-source', 'native:' + str(command[2]) if command[2] >= 0 else 'off'])


    def _poll_ended(self, state):
        if self.requested and (self.loaded or self.finished) and not state.get('eof') and state.get('state') == 'stopped':
            self.loaded = self.finished = False
            self.stop_count += 1
            self.emit({'event':'end-file', 'reason':'stop'})
            return True
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
            return True
        return False

    def _poll_loading(self, state):
        if state.get('input_state') == 5:
            self.input_error = True
        if state.get('input') and state.get('input_state') in (2, 3) and not self.loaded:
            if self.pause_when_ready:
                self.api('pause', value='true')
                self.pause_when_ready = False
                state = dict(state, state='paused')
            self.loaded = True
            self.apply_pending_subtitle()
            self.emit({'event':'file-loaded'})
        return state

    def restore_subtitle_choice(self, state):
        choice = getattr(self, 'subtitle_choice', None)
        if not choice:
            return False
        if choice == 'provided' and self.subtitle_loading:
            if state.get('sid', -1) >= 0:
                self.api('subtitle', value=-1)
            return True
        for option in self.subtitle_tracks()['options']:
            if choice in (option['id'], option['label']):
                self.subtitle_choice = None
                self.select_subtitle_source(option['id'])
                return True
        # Embedded tracks may appear after playback starts. Keep looking and
        # use the default selection in the meantime.
        return False

    def _poll_subtitles(self, state):
        if self.provided_cues and not provided_cues_usable(self.provided_cues, state.get('duration', 0)):
            self.provided_cues = []
            if self.subtitle_source == 'provided':
                self.subtitle_revision = 0
        if self.subtitle_revision:
            if self.subtitle_source in ('off', 'provided', 'whisper') and state.get('sid', -1) >= 0:
                self.api('subtitle', value=-1)
            return
        if self.restore_subtitle_choice(state):
            return

        sid = state.get('sid', -1)
        native_ids = [track['id'] for track in self.english_tracks(state)]
        if native_ids:
            preferred = sid if sid in native_ids else native_ids[0]
            if sid != preferred:
                self.api('subtitle', value=preferred)
            source = f'native:{preferred}'
        else:
            if sid >= 0:
                self.api('subtitle', value=-1)
            source = 'off'
            if self.provided_cues:
                source = 'provided'
            elif not self.subtitle_loading and self.live_enabled:
                source = 'whisper'
        if source != self.subtitle_source:
            self.set_caption_source(source)

    def _publish_properties(self, state):
        whisper_active = self.subtitle_source in ('provided', 'whisper') and self.caption_requested
        native_active = self.subtitle_source.startswith('native:')
        subtitle_id = int(self.subtitle_source.split(':')[1]) if native_active else False
        values = {'time-pos':state.get('time',0), 'duration':state.get('duration',0), 'pause':state.get('state') == 'paused',
                  'sid': self.subtitle_source if whisper_active else subtitle_id,
                  'sub-visibility': whisper_active or native_active,
                  'whisper-captions': whisper_active and self.subtitle_source == 'whisper',
                  'subtitle-tracks': self.subtitle_tracks(),
                  'chapter-info': {'index': state.get('chapter', -1), 'count': state.get('chapter_count', 0),
                                   'name': state.get('chapter_name', '')}}
        for name, value in values.items():
            if self.last.get(name) != value:
                self.last[name] = value
                self.emit({'event':'property-change','name':name,'data':value})
        return whisper_active

    def _render_caption(self, state, whisper_active):
        now = time.monotonic()
        text = ''
        if whisper_active:
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

    def poll(self, state):
        self.last_state = state
        if self._poll_ended(state):
            return
        if not self.requested or self.finished or state.get('eof'):
            return
        state = self._poll_loading(state)
        if not self.loaded:
            return
        self._poll_subtitles(state)
        whisper_active = self._publish_properties(state)
        self._render_caption(state, whisper_active)

    def _wait_for_api(self):
        for _ in range(100):
            if self.closed.is_set() or self.process.poll() is not None:
                return False
            try:
                self.api()
                break
            except OSError:
                time.sleep(.05)
        else:
            raise RuntimeError('Could not connect to VLC.')
        return True

    def monitor(self):
        self.log_offset = 0
        try:
            if not self._wait_for_api():
                return
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
            stream_relay.release(self)
            self.process.wait()
            self.directory.cleanup()
            self.emit({'event':'process-exited','code':self.process.returncode,
                       'error': bool(getattr(self, 'last_error', None))})

    def close(self):
        self.closed.set()
        stream_relay.release(self)
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
