"""Measure the production EQ in private PipeWire; hardware monitors are disabled."""
import array
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'system/apps/shell/scripts'))
from audio_equalizer import Equalizer, command, pulse_list
from audio_eq_dsp import PRESETS, SINK, response_db, headroom


def measure(root, frequency):
    path = root / 'tone.wav'
    samples = array.array('h', [round(3276 * math.sin(2*math.pi*frequency*i/48000))
                               for i in range(48000) for _ in range(2)])
    with wave.open(str(path), 'wb') as output:
        output.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
        output.writeframes(samples.tobytes())
    capture = root / 'capture.raw'
    with capture.open('wb') as stream:
        recording = subprocess.Popen(['parec', '--device=eq_test.monitor', '--format=float32le',
                                      '--rate=48000', '--channels=2', '--latency-msec=20'], stdout=stream)
        try:
            time.sleep(.15)
            subprocess.run(['paplay', '--device='+SINK, str(path)], check=True, timeout=5)
            time.sleep(.15)
        finally:
            recording.terminate()
            recording.wait(timeout=3)
    values = array.array('f')
    values.frombytes(capture.read_bytes())
    size = 9600
    rms = max(math.sqrt(sum(value*value for value in values[i:i+size])/size)
              for i in range(0, len(values)-size, size))
    return 20*math.log10(rms / (.1/math.sqrt(2)))


def private_session(root):
    config = root / 'config/wireplumber/wireplumber.conf.d'
    config.mkdir(parents=True)
    (config/'99-no-hardware.conf').write_text('wireplumber.profiles = { main = { hardware.audio = disabled hardware.bluetooth = disabled hardware.video-capture = disabled } }\n')
    processes = []
    equalizer = None
    try:
        for program in ('pipewire', 'pipewire-pulse', 'wireplumber'):
            with (root/(program+'.log')).open('w') as log:
                processes.append(subprocess.Popen([program], stdout=log, stderr=log))
            time.sleep(.3)
        command('pactl', 'load-module', 'module-null-sink', 'sink_name=eq_test')
        command('pactl', 'set-default-sink', 'eq_test')
        equalizer = Equalizer()
        for preset in ('Flat', 'Bass'):
            equalizer.configure({'enabled': True, 'gains': PRESETS[preset], 'preset':preset})
            equalizer.tick()
            assert not equalizer.error, equalizer.error
            assert command('pactl', 'get-default-sink') == SINK
            for frequency in (62.5, 4000):
                measured = measure(root, frequency)
                expected = response_db(PRESETS[preset], frequency) + headroom(PRESETS[preset])
                print(f'{preset} {frequency:g} Hz: measured {measured:.2f} dB; expected {expected:.2f} dB', flush=True)
                assert abs(measured-expected) < .8, (measured, expected)
        equalizer.process.kill()
        equalizer.process.wait(timeout=3)
        equalizer.tick()
        assert equalizer.process.poll() is None and not equalizer.error
        equalizer.configure({'enabled':False})
        equalizer.tick()
        assert command('pactl', 'get-default-sink') == 'eq_test'
        assert all(sink['name'] != SINK for sink in pulse_list('sinks'))
        print('EQ SIGNAL, LIVE UPDATE, FILTER RECOVERY AND BYPASS PASSED', flush=True)
    finally:
        if equalizer:
            equalizer.stop()
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


class PipeWireEqualizerTests(unittest.TestCase):
    @unittest.skipUnless(all(shutil.which(tool) for tool in ('pipewire', 'pipewire-pulse', 'wireplumber', 'pactl', 'pw-cli', 'parec', 'paplay', 'dbus-run-session')), 'PipeWire test tools required')
    def test_signal_and_routing(self):
        with tempfile.TemporaryDirectory(prefix='enclosure-eq-test-') as folder:
            root = Path(folder)
            runtime = root/'run'
            runtime.mkdir(mode=0o700)
            env = dict(os.environ, HOME=folder, XDG_RUNTIME_DIR=str(runtime), PIPEWIRE_RUNTIME_DIR=str(runtime),
                       PULSE_SERVER='unix:'+str(runtime/'pulse/native'), XDG_CONFIG_HOME=str(root/'config'),
                       XDG_STATE_HOME=str(root/'state'), XDG_CACHE_HOME=str(root/'cache'))
            env.pop('DBUS_SESSION_BUS_ADDRESS', None)
            result = subprocess.run(['dbus-run-session', '--', sys.executable, __file__, '--session', folder],
                                    env=env, capture_output=True, text=True, timeout=35)
            logs = '\n'.join(path.read_text()[-1200:] for path in root.glob('*.log'))
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr+logs)
            self.assertIn('EQ SIGNAL, LIVE UPDATE, FILTER RECOVERY AND BYPASS PASSED', result.stdout)
            print(result.stdout.strip())


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--session':
        private_session(Path(sys.argv[2]))
    else:
        unittest.main()
