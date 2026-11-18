"""Exercise the downloader protocol with a fake executable; no network or login."""
import importlib.util
import json
import os
import queue
import threading
from pathlib import Path
import subprocess
import tempfile
import unittest

SERVICE = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/music_downloads/service.py'

class Downloads(unittest.TestCase):
    def test_sync_publication_validates_and_keeps_audio(self):
        spec = importlib.util.spec_from_file_location('download_commands', SERVICE.parent/'commands.py')
        commands = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(commands)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            commands.remember_playlist_source(folder, 'https://open.spotify.com/playlist/'+'a'*22)
            audio = folder/'old.ogg'
            audio.write_bytes(b'audio')
            result = folder/'result.spotdl'
            result.write_text(json.dumps([dict(song_id='b'*22, name='Song', artist='Artist')]))
            commands.publish_playlist(folder, result)
            metadata = folder/'.enclosure-playlist.json'
            before = metadata.read_text()
            result.write_text('[{}]')
            with self.assertRaises(ValueError):
                commands.publish_playlist(folder, result)
            self.assertEqual(metadata.read_text(), before)
            result.write_text('[]')
            commands.publish_playlist(folder, result)
            self.assertEqual(json.loads(metadata.read_text())['tracks'], [])
            self.assertEqual(audio.read_bytes(), b'audio')

    def test_cookie_selection_persists_and_clear_forgets(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            env = {**os.environ, 'HOME': directory, 'XDG_STATE_HOME': str(home/'state'),
                   'PYTHONDONTWRITEBYTECODE': '1'}
            def session(messages):
                result = subprocess.run(['python3', '-u', str(SERVICE)],
                    input=''.join(json.dumps(m)+'\n' for m in messages),
                    capture_output=True, text=True, env=env, check=True, timeout=10)
                return [json.loads(line) for line in result.stdout.splitlines()]
            cookie = str(home/'cookies with spaces.txt')
            self.assertEqual(session([dict(settingsGet=True)])[0]['settings']['cookieFile'], '')
            self.assertEqual(session([dict(settingsCookieFile=cookie)])[0]['settings']['cookieFile'], cookie)
            self.assertEqual(session([dict(settingsGet=True)])[0]['settings']['cookieFile'], cookie)
            saved = home/'state/enclosure/music/downloads.json'
            self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(saved.read_text()), dict(cookieFile=cookie))
            session([dict(settingsCookieFile='')])
            self.assertEqual(session([dict(settingsGet=True)])[0]['settings']['cookieFile'], '')
            saved.write_text('invalid json')
            self.assertEqual(session([dict(settingsGet=True)])[0]['settings']['cookieFile'], '')

    def test_mix_download_preserves_track_identity(self):
        spec = importlib.util.spec_from_file_location('download_commands', SERVICE.parent/'commands.py')
        commands = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(commands)
        links = 'https://open.spotify.com/playlist/'+'a'*22
        args = commands.build_spotdl_args(0, links, '/tmp/Music/Daily Mixes/test', 'ogg', mix_tracks=True)
        self.assertEqual(args[args.index('--output')+1], '/tmp/Music/Daily Mixes/test/{track-id}.{output-ext}')
        self.assertEqual(args[1], links)
        self.assertEqual(args[args.index('--threads')+1], '2')
        self.assertNotIn('--use-cache-file', args)
        with self.assertRaises(ValueError):
            commands.build_spotdl_args(0, 'invalid', '/tmp/Music', 'ogg', mix_tracks=True)

    def test_cookie_file_validation_and_arguments(self):
        spec = importlib.util.spec_from_file_location('download_commands', SERVICE.parent/'commands.py')
        commands = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(commands)
        link = 'https://open.spotify.com/track/abc'
        with tempfile.TemporaryDirectory() as directory:
            cookies = Path(directory) / 'cookies with spaces.txt'
            cookies.write_text('# Netscape HTTP Cookie File\n')
            for mix in (False, True):
                args = commands.build_spotdl_args(0, link, directory, 'ogg', mix_tracks=mix, cookie_file=str(cookies))
                self.assertEqual(args[args.index('--cookie-file')+1], str(cookies))
            self.assertNotIn('--cookie-file', commands.build_spotdl_args(0, link, directory, 'ogg'))
            for invalid in ('relative.txt', str(Path(directory)/'missing'), directory, True):
                with self.assertRaises(ValueError):
                    commands.build_spotdl_args(0, link, directory, 'ogg', cookie_file=invalid)
            cookies.write_text('{"cookies": "not a Netscape export"}')
            with self.assertRaises(ValueError):
                commands.build_spotdl_args(0, link, directory, 'ogg', cookie_file=str(cookies))

    def test_warm_imports_once_and_isolates_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            package = folder / 'spotdl/console'
            package.mkdir(parents=True)
            (package.parent / '__init__.py').write_text('')
            (package / '__init__.py').write_text('')
            (package / 'entry_point.py').write_text(
                "import os\nprint('imported', flush=True)\n"
                "def console_entry_point():\n"
                "    print('job ' + str(os.getpid()), flush=True)\n")
            (folder / 'SpotipyFree.py').write_text('class Spotify:\n    def track(self): pass\n')
            proc = subprocess.Popen(['python3', '-u', str(SERVICE.with_name('warm.py')), '--native'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                env={**os.environ, 'PYTHONPATH': directory, 'PYTHONDONTWRITEBYTECODE': '1'})
            try:
                self.assertEqual(proc.stdout.readline().strip(), 'imported')
                pids = []
                for _ in range(2):
                    proc.stdin.write('["spotdl", "download"]\n'); proc.stdin.flush()
                    pid = json.loads(proc.stdout.readline())['pid']
                    pids.append(pid)
                    self.assertEqual(json.loads(proc.stdout.readline())['log'], 'job ' + str(pid))
                    self.assertEqual(json.loads(proc.stdout.readline())['code'], 0)
                    self.assertIsNone(proc.poll())
                self.assertNotEqual(*pids)
            finally:
                proc.stdin.close(); proc.wait(timeout=5); proc.stdout.close()

    def test_metadata_cache_hits_expiry_and_corruption(self):
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location('track_cache', SERVICE.with_name('track_cache.py'))
        cache = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache)
        class Client:
            getIsrc = False
            def isUrl(self, value): return False
        calls = []
        @cache.cached_track
        def fetch(client, identity):
            calls.append(identity)
            return {'id': identity}
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, XDG_CACHE_HOME=directory):
            self.assertEqual(fetch(Client(), 'abc'), {'id': 'abc'})
            fetch(Client(), 'abc')
            self.assertEqual(len(calls), 1)
            path = next(Path(directory).rglob('*.json'))
            os.utime(path, (0, 0))
            fetch(Client(), 'abc')
            self.assertEqual(len(calls), 2)
            path.write_text('broken')
            fetch(Client(), 'abc')
            self.assertEqual(len(calls), 3)

    def test_cancel_stubborn_parent_and_surviving_child(self):
        for mode in ('stubborn', 'childonly'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                executable = home/'.local/share/venvs/spotdl/bin/spotdl'
                executable.parent.mkdir(parents=True)
                executable.write_text("""#!/usr/bin/python3
import os, signal, sys, time
if 'fast' in ' '.join(sys.argv):
    print('finished fast', flush=True)
    sys.exit(0)
if 'stubborn' in ' '.join(sys.argv):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
if os.fork() == 0:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    print('ready ' + str(os.getpid()), flush=True)
    time.sleep(60)
    sys.exit(0)
time.sleep(60)
""")
                executable.chmod(0o755)
                proc = subprocess.Popen(['python3', '-u', str(SERVICE)], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, text=True, env={**os.environ, 'HOME': directory, 'PYTHONDONTWRITEBYTECODE': '1'})
                messages = queue.Queue()
                def collect():
                    for line in proc.stdout:
                        messages.put(json.loads(line))
                reader = threading.Thread(target=collect, daemon=True)
                reader.start()
                def send(**data):
                    proc.stdin.write(json.dumps(data)+'\n'); proc.stdin.flush()
                try:
                    send(links='https://open.spotify.com/track/'+mode)
                    self.assertTrue(messages.get(timeout=5)['started'])
                    child_pid = int(messages.get(timeout=5)['log'].split()[-1])
                    send(cancel=True)
                    send(cancel=True)  # Repeated clicks must not reset the deadline.
                    done = messages.get(timeout=6)
                    self.assertTrue(done['done'])
                    self.assertTrue(done['cancelled'])
                    status = Path('/proc')/str(child_pid)/'stat'
                    if status.exists():
                        self.assertEqual(status.read_text().split()[2], 'Z', 'Download child is still running')
                    send(links='https://open.spotify.com/track/fast')
                    self.assertTrue(messages.get(timeout=5)['started'])
                    self.assertEqual(messages.get(timeout=5)['log'], 'finished fast')
                    self.assertEqual(messages.get(timeout=5)['code'], 0)
                finally:
                    proc.stdin.close()
                    proc.wait(timeout=6)
                    reader.join(timeout=1)
                    proc.stdout.close()

    def test_validation_completion_and_cancel(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            executable = home/'.local/share/venvs/spotdl/bin/spotdl'
            executable.parent.mkdir(parents=True)
            executable.write_text('#!/usr/bin/python3\nimport sys,time\nprint(sys.argv[sys.argv.index("--cookie-file")+1] if "--cookie-file" in sys.argv else "fake track",flush=True)\nif "slow" in " ".join(sys.argv): time.sleep(30)\n')
            executable.chmod(0o755)
            proc = subprocess.Popen(['python3','-u',str(SERVICE)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,env={**os.environ,'HOME':directory,'PYTHONDONTWRITEBYTECODE':'1'})
            def send(**data):
                proc.stdin.write(json.dumps(data)+'\n'); proc.stdin.flush()
            def read(): return json.loads(proc.stdout.readline())
            try:
                send(backend='zotify', links='https://open.spotify.com/track/abc')
                self.assertIn('Only spotDL', read()['error'])
                send(links='invalid')
                self.assertIn('error',read())
                send(links='https://open.spotify.com/track/abc')
                self.assertTrue(read()['started'])
                self.assertEqual(read()['log'],'fake track')
                self.assertEqual(read()['code'],0)
                self.assertTrue((home/'Music').is_dir())
                cookies = home/'session cookies.txt'
                cookies.write_text('# Netscape HTTP Cookie File\n')
                send(links='https://open.spotify.com/track/abc', cookieFile=str(cookies), mixTracks=True)
                self.assertTrue(read()['started'])
                self.assertEqual(read()['log'], str(cookies))
                self.assertEqual(read()['code'], 0)
                send(links='https://open.spotify.com/track/abc', cookieFile=str(home/'missing'))
                self.assertIn('unreadable', read()['error'])
                send(links='https://open.spotify.com/track/slow')
                self.assertTrue(read()['started']); self.assertEqual(read()['log'],'fake track')
                send(cancel=True)
                self.assertNotEqual(read()['code'],0)
            finally:
                proc.stdin.close(); proc.wait(timeout=5); proc.stdout.close()

if __name__ == '__main__': unittest.main()
