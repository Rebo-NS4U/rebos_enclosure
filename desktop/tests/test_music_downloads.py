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
    def test_mix_download_preserves_track_identity(self):
        spec = importlib.util.spec_from_file_location('download_commands', SERVICE.parent/'commands.py')
        commands = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(commands)
        links = 'https://open.spotify.com/track/'+'b'*22
        args = commands.build_spotdl_args(0, links, '/tmp/Music/Daily Mixes/test', 'ogg', mix_tracks=True)
        self.assertEqual(args[args.index('--output')+1], '/tmp/Music/Daily Mixes/test/{track-id}.{output-ext}')
        self.assertEqual(args[1], links)
        with self.assertRaises(ValueError):
            commands.build_spotdl_args(0, 'invalid', '/tmp/Music', 'ogg', mix_tracks=True)

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
            executable.write_text('#!/usr/bin/python3\nimport sys,time\nprint("fake track",flush=True)\nif "slow" in " ".join(sys.argv): time.sleep(30)\n')
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
                send(links='https://open.spotify.com/track/slow')
                self.assertTrue(read()['started']); self.assertEqual(read()['log'],'fake track')
                send(cancel=True)
                self.assertNotEqual(read()['code'],0)
            finally:
                proc.stdin.close(); proc.wait(timeout=5); proc.stdout.close()

if __name__ == '__main__': unittest.main()
