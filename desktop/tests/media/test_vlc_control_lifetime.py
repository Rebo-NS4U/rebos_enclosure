"""Exercise the private Lua HTTP interface in a real, isolated VLC process."""
import base64
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener


@unittest.skipUnless(shutil.which('vlc') and shutil.which('ffmpeg'), 'VLC and FFmpeg required')
class ControlLifetimeTests(unittest.TestCase):
    def test_playback_and_callbacks_survive_interface_setup_returning(self):
        with tempfile.TemporaryDirectory(prefix='vlc-control-lifetime-') as folder:
            home = Path(folder)
            helper = home / '.local/share/vlc/lua/intf/media_browser.lua'
            helper.parent.mkdir(parents=True)
            source = Path(__file__).resolve().parents[3] / 'system/apps/media/vlc_control.lua'
            shutil.copyfile(source, helper)
            chapters = home / 'chapters.ffmeta'
            chapters.write_text(
                ';FFMETADATA1\n'
                '[CHAPTER]\nTIMEBASE=1/1\nSTART=0\nEND=30\ntitle=Opening\n'
                '[CHAPTER]\nTIMEBASE=1/1\nSTART=30\nEND=60\ntitle=Episode\n'
                '[CHAPTER]\nTIMEBASE=1/1\nSTART=60\nEND=120\ntitle=Credits\n')
            video = home / 'clip.mkv'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'testsrc2=s=64x64:d=120:r=10', '-i', str(chapters),
                            '-map_chapters', '1', '-c:v', 'libx264', str(video)],
                           check=True, capture_output=True, timeout=20)
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                port = listener.getsockname()[1]
            # Never write a test helper or VLC settings into the running desktop.
            env = {**os.environ, 'HOME': folder, 'XDG_DATA_HOME': str(home / '.local/share'),
                   'XDG_CONFIG_HOME': str(home / '.config'),
                   'XDG_CACHE_HOME': str(home / '.cache'), 'XDG_STATE_HOME': str(home / '.state')}
            opener = build_opener(ProxyHandler({}))
            logpath = home / 'vlc.log'
            with logpath.open('w') as log:
                player = subprocess.Popen([
                    'vlc', '--ignore-config', '--no-one-instance', '-I', 'dummy',
                    '--vout=dummy', '--aout=dummy', '--verbose=2',
                    '--extraintf=luaintf', '--lua-intf=media_browser',
                    '--http-host=127.0.0.1', f'--http-port={port}',
                    f'--lua-config=media_browser={{port={port},password="test"}}'],
                    env=env, stdout=log, stderr=log)
                def api(**values):
                    self.assertIsNone(player.poll(), logpath.read_text(errors='replace')[-4000:])
                    request = Request(f'http://127.0.0.1:{port}/session.json?' + urlencode(values),
                                      headers={'Authorization': 'Basic ' + base64.b64encode(b':test').decode()})
                    with opener.open(request, timeout=2) as response:
                        state = json.load(response)
                    self.assertTrue(state['ok'], state)
                    return state
                try:
                    deadline = time.monotonic() + 10
                    while True:
                        try:
                            api()
                            break
                        except URLError:
                            if time.monotonic() >= deadline:
                                self.fail('VLC control endpoint did not start: ' +
                                          logpath.read_text(errors='replace')[-4000:])
                            time.sleep(.05)
                    api(command='load', data=json.dumps({'generation': 1, 'url': video.as_uri(),
                                                        'title': 'Control lifetime test', 'options': []}))
                    duration = float(os.environ.get('VLC_CONTROL_STRESS_SECONDS', '20'))
                    deadline = time.monotonic() + duration
                    requests = 0
                    advanced = False
                    while time.monotonic() < deadline:
                        state = api()
                        advanced |= state.get('time', 0) > 1
                        api(command='caption', value='Playback stress test')
                        api(command='clear-caption')
                        requests += 3
                        # Cross many former one-second timer wakeups while
                        # callbacks allocate and collect Lua/VLC objects.
                        time.sleep(.01)
                    self.assertGreater(requests, 100)
                    self.assertTrue(advanced, 'Playback never advanced')
                    api(command='pause', value='true')
                    self.assertEqual(api()['state'], 'paused')
                    api(command='seek', value='3')
                    opening = api()
                    self.assertEqual(opening['chapter_name'].strip(), 'Opening')
                    self.assertIsNotNone(opening['next_chapter'])
                    api(command='skip-intro', value=opening['chapter'])
                    deadline = time.monotonic() + 2
                    while True:
                        state = api()
                        at_destination = state['chapter_name'].strip() == 'Episode' and abs(state['time'] - 30) < 1
                        if at_destination or time.monotonic() >= deadline:
                            break
                        time.sleep(.05)
                    self.assertEqual(state['chapter_name'].strip(), 'Episode')
                    self.assertAlmostEqual(state['time'], 30, delta=1)
                    api(command='skip-intro', value=opening['chapter'])
                    self.assertEqual(api()['chapter_name'].strip(), 'Episode')
                    api(command='pause', value='false')
                    self.assertIsNone(player.poll())
                    self.assertIn('Received first picture', logpath.read_text(errors='replace'))
                    print(f'VLC playback survived {requests} control requests over {duration:g}s')
                finally:
                    if player.poll() is None:
                        player.terminate()
                    try:
                        player.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        player.kill()
                        player.wait(timeout=5)
