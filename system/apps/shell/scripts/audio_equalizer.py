#!/usr/bin/env python3
"""Independent, opt-in equalizer service. Never restarts the audio server."""
import json
import os
from pathlib import Path
import selectors
import signal
import socket
import subprocess
import sys
import time

from audio_eq_dsp import SINK, OUTPUT, PRESETS, validate_gains, graph, controls, headroom


def command(*args, json_output=False):
    result = subprocess.run(args, check=True, capture_output=True, text=True, timeout=5)
    return json.loads(result.stdout) if json_output else result.stdout.strip()


def pulse_list(kind):
    return command('pactl', '--format=json', 'list', kind, json_output=True)


def socket_path():
    return Path(os.environ['XDG_RUNTIME_DIR']) / 'enclosure-audio-eq.sock'


class Equalizer:
    def __init__(self):
        self.path = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'enclosure/audio-equalizer.json'
        self.settings = {'enabled': False, 'gains': PRESETS['Flat'][:], 'preset': 'Flat', 'target': ''}
        self.process = None
        self.target = ''
        self.error = ''
        self.applied = None
        try:
            self.configure(json.loads(self.path.read_text()), save=False)
        except FileNotFoundError:
            pass
        except (ValueError, OSError):
            self.error = 'Saved EQ settings could not be loaded; using bypass.'

    def configure(self, data, save=True):
        if not isinstance(data, dict):
            raise ValueError("Invalid EQ settings")
        gains = validate_gains(data.get('gains', self.settings['gains']))
        enabled = data.get('enabled', self.settings['enabled'])
        if not isinstance(enabled, bool):
            raise ValueError('Invalid bypass setting')
        preset = data.get('preset', self.settings['preset'])
        if preset not in PRESETS and preset != 'Custom':
            raise ValueError('Unknown EQ preset')
        target = data.get('target', self.settings['target'])
        if not isinstance(target, str) or target in (SINK, OUTPUT) or len(target) > 512:
            raise ValueError('Choose a physical output device')
        self.settings = dict(enabled=enabled, gains=gains, preset=preset, target=target)
        if save:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.settings) + '\n')
            temporary.chmod(0o600)
            temporary.replace(self.path)

    def status(self):
        return dict(self.settings, active=self.process is not None and self.process.poll() is None,
                    error=self.error, headroom=headroom(self.settings['gains']), output=self.target)

    def move_streams(self, source, destination, inputs):
        for stream in inputs:
            if stream.get('sink') == source and stream.get('properties', {}).get('node.name') != OUTPUT:
                try:
                    command('pactl', 'move-sink-input', str(stream['index']), destination)
                except subprocess.CalledProcessError:
                    pass  # A stream may end between discovery and routing.

    def stop(self):
        if self.process is None:
            return
        try:
            sinks = pulse_list('sinks')
            equalizer = next((sink for sink in sinks if sink['name'] == SINK), None)
            physical = next((sink for sink in sinks if sink['name'] == self.target), None)
            if equalizer and physical:
                if command('pactl', 'get-default-sink') == SINK:
                    command('pactl', 'set-default-sink', self.target)
                self.move_streams(equalizer['index'], self.target, pulse_list('sink-inputs'))
        except (OSError, subprocess.SubprocessError):
            pass  # Disconnected PipeWire has already released the virtual device.
        self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)
        self.process = None
        self.applied = None

    def start(self, target):
        self.target = target
        config = socket_path().with_suffix('.conf')
        config.write_text(json.dumps(graph(self.settings['gains'], target)))
        config.chmod(0o600)
        self.process = subprocess.Popen(['pipewire', '-c', str(config)],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.applied = None
        for _ in range(40):
            if self.process.poll() is not None:
                raise RuntimeError('PipeWire could not start the equalizer filter')
            sinks = pulse_list('sinks')
            if any(sink['name'] == SINK for sink in sinks):
                return
            time.sleep(.05)
        raise RuntimeError('Equalizer device did not become available')

    def update_controls(self):
        gains = self.settings['gains']
        if self.applied == gains:
            return
        nodes = command('pw-dump', json_output=True)
        node = next((node for node in nodes if node.get('info', {}).get('props', {}).get('node.name') == SINK), None)
        if not node:
            raise RuntimeError('Equalizer device disconnected')
        params = [value for pair in controls(gains).items() for value in pair]
        command('pw-cli', 'set-param', str(node['id']), 'Props', json.dumps({'params': params}))
        self.applied = gains[:]

    def reconcile(self):
        self.error = ''
        if not self.settings['enabled']:
            self.stop()
            return
        sinks = pulse_list('sinks')
        devices = [sink['name'] for sink in sinks if sink['name'] != SINK]
        if not devices:
            self.stop()
            raise RuntimeError('No output device is available')
        default = command('pactl', 'get-default-sink')
        target = self.settings['target'] or (default if default != SINK else self.target)
        target = target if target in devices else devices[0]
        if self.process and self.process.poll() is not None:
            self.process = None
            self.applied = None
        if not self.process:
            self.start(target)
        inputs = pulse_list('sink-inputs')
        if self.target != target:
            for stream in inputs:
                if stream.get('properties', {}).get('node.name') == OUTPUT:
                    command('pactl', 'move-sink-input', str(stream['index']), target)
            self.target = target
        self.update_controls()
        if default != SINK:
            previous = next((sink for sink in sinks if sink['name'] == default), None)
            command('pactl', 'set-default-sink', SINK)
            if previous:
                self.move_streams(previous['index'], SINK, inputs)

    def tick(self):
        try:
            self.reconcile()
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            self.error = str(error)[:240]
            self.stop()


def serve():
    path = socket_path()
    path.unlink(missing_ok=True)
    server = socket.socket(socket.AF_UNIX)
    server.bind(str(path))
    path.chmod(0o600)
    server.listen(4)
    server.setblocking(False)
    equalizer = Equalizer()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(server, selectors.EVENT_READ)
            equalizer.tick()
            while True:
                for _, _events in selector.select(timeout=2):
                    with server.accept()[0] as connection:
                        connection.settimeout(2)
                        try:
                            data = connection.makefile().readline(8192)
                            request = json.loads(data)
                            if not isinstance(request, dict):
                                raise ValueError("Invalid EQ request")
                            if request.get('action') == 'configure':
                                equalizer.configure(request)
                                equalizer.tick()
                            connection.sendall((json.dumps(equalizer.status()) + '\n').encode())
                        except (ValueError, OSError) as error:
                            equalizer.error = str(error)[:240]
                equalizer.tick()
    finally:
        equalizer.stop()
        server.close()
        path.unlink(missing_ok=True)
        path.with_suffix('.conf').unlink(missing_ok=True)


def client(request):
    path = socket_path()
    if not path.exists():
        command('systemctl', '--user', 'start', 'rebos-equalizer.service')
    for _ in range(30):
        try:
            with socket.socket(socket.AF_UNIX) as connection:
                connection.settimeout(8)
                connection.connect(str(path))
                connection.sendall((json.dumps(request) + "\n").encode())
                return json.loads(connection.makefile().readline())
        except (FileNotFoundError, ConnectionRefusedError):
            command("systemctl", "--user", "start", "rebos-equalizer.service")
            time.sleep(.1)
    raise RuntimeError('Equalizer service is unavailable')


if __name__ == '__main__':
    try:
        if len(sys.argv) > 1 and sys.argv[1] == 'serve':
            serve()
        else:
            print(json.dumps(client(json.loads(sys.argv[1]) if len(sys.argv) > 1 else {})))
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as failure:
        print(json.dumps({'error': str(failure)[:240], 'active': False}))
        sys.exit(1)
