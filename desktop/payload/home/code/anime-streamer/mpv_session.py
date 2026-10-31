"""One mpv process with a persistent IPC channel for episode transitions."""
import json
import queue
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from gi.repository import GLib


class MpvSession:
    def __init__(self, settings, on_event, logpath, extra_args=()):
        self.on_event = on_event
        self.commands = queue.Queue()
        self.closed = threading.Event()
        self.tracks = ('', '')
        self.directory = tempfile.TemporaryDirectory(prefix='anime-player-')
        self.socket_path = self.directory.name + '/ipc'
        args = ['mpv', '--no-terminal', '--idle=yes', '--force-window=yes', '--keep-open=no',
                '--loop-file=no', '--loop-playlist=no', '--save-position-on-quit=yes',
                f'--volume={settings["volume"]}', '--input-ipc-server=' + self.socket_path]
        player_config = Path.home() / '.local/share/anime-streamer/player'
        if (player_config / 'mpv.conf').is_file():
            args.append('--config-dir=' + str(player_config))
        if settings['fullscreen']:
            args.append('--fullscreen')
        args.extend(extra_args)
        Path(logpath).parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(logpath, 'w') as log:
                self.process = subprocess.Popen(args, stdout=log, stderr=log)
        except Exception:
            self.directory.cleanup()
            raise
        self.command(['observe_property', 1, 'time-pos'])
        self.command(['observe_property', 2, 'duration'])
        self.command(['observe_property', 3, 'pause'])
        self.command(['observe_property', 4, 'sid'])
        self.command(['observe_property', 5, 'sub-visibility'])
        threading.Thread(target=self.monitor, daemon=True).start()

    def command(self, command):
        if not self.closed.is_set():
            self.commands.put(command)

    def load(self, links, title, paused=False):
        video, referer, subtitles, audio = links
        self.tracks = (subtitles, audio)
        self.command(['set_property', 'pause', paused])
        options = {'referrer': referer, 'force-media-title': title, 'pause': 'yes' if paused else 'no'}
        if getattr(links, 'audio_language', ''):
            options['alang'] = links.audio_language
        if getattr(links, 'is_hls', False):
            options['demuxer-lavf-o'] = 'allowed_extensions=ALL,allowed_segment_extensions=ALL,extension_picky=0'
        self.command(['loadfile', video, 'replace', -1, options])

    def emit(self, event):
        GLib.idle_add(self.on_event, event)

    def clear_captions(self):
        self.command(['script-message-to', 'live_captions', 'anime-captions-clear'])

    def update_captions(self, path):
        self.command(['script-message-to', 'live_captions', 'anime-captions-file', path])

    def show_captions(self):
        self.command(['script-message-to', 'live_captions', 'anime-captions-show'])

    def monitor(self):
        connection = socket.socket(socket.AF_UNIX)
        pending = {}
        sequence = 0
        try:
            for _ in range(200):
                if self.closed.is_set() or self.process.poll() is not None:
                    return
                try:
                    connection.connect(self.socket_path)
                    break
                except OSError:
                    time.sleep(.025)
            else:
                raise RuntimeError('Could not connect to the player')
            connection.settimeout(.05)
            buffer = b''
            while not self.closed.is_set() and self.process.poll() is None:
                while not self.commands.empty():
                    command = self.commands.get_nowait()
                    sequence += 1
                    pending[sequence] = command[0]
                    connection.sendall((json.dumps({'command': command, 'request_id': sequence}) + '\n').encode())
                try:
                    data = connection.recv(65536)
                except socket.timeout:
                    continue
                if not data:
                    if self.process.poll() is None and not self.closed.is_set():
                        raise RuntimeError('Player disconnected')
                    break
                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if 'request_id' in event:
                        command_name = pending.pop(event['request_id'], '')
                        if event.get('error', 'success') != 'success':
                            self.emit({'event': 'command-error', 'command': command_name, 'error': event['error']})
                    else:
                        if event.get('event') == 'file-loaded':
                            subtitles, audio = self.tracks
                            if subtitles:
                                self.command(['sub-add', subtitles, 'select'])
                            if audio:
                                self.command(['audio-add', audio, 'select'])
                        self.emit(event)
        except (OSError, RuntimeError) as error:
            if not self.closed.is_set():
                self.emit({'event': 'connection-error', 'error': str(error)})
                if self.process.poll() is None:
                    self.process.terminate()
        finally:
            connection.close()
            self.process.wait()
            self.directory.cleanup()
            self.emit({'event': 'process-exited', 'code': self.process.returncode})

    def close(self):
        self.closed.set()
        if self.process.poll() is None:
            self.process.terminate()
