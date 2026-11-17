"""Exercise the downloader protocol with a fake executable; no network or login."""
import importlib.util
import json
import os
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
