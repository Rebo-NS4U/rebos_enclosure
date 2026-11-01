"""Verify theme rendering and permission setup without changing the real greeter."""
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import greeter_sync


class GreeterSyncTests(unittest.TestCase):
    def test_wallpaper_and_color_changes(self):
        script = runpy.run_path(str(ROOT / 'payload/home/.local/bin/regreet-sync'))
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            cache, target = home / 'cache', home / 'theme'
            cache.mkdir()
            target.mkdir()
            config = home / '.config/regreet-sync'
            config.mkdir(parents=True)
            (config / 'regreet.css.in').write_text('window {color: {{primary}};}')
            wall = home / 'wall.png'
            Image.new('RGB', (16, 16), 'red').save(wall)
            (cache / 'wallpapers.json').write_text(json.dumps({'currentWall': str(wall)}))
            palette = cache / 'effective-palette.json'
            palette.write_text('{"primary":"#112233"}')
            sync = script['main']
            sync.__globals__.update(HOME=home, CACHE=cache, TARGET=target)
            sync()
            self.assertIn('#112233', (target / 'regreet.css').read_text())
            timestamp = (target / 'background.png').stat().st_mtime_ns
            sync()
            self.assertEqual(timestamp, (target / 'background.png').stat().st_mtime_ns)
            palette.write_text('{"primary":"#abcdef"}')
            sync()
            self.assertIn('#abcdef', (target / 'regreet.css').read_text())
            Image.new('RGB', (16, 16), 'blue').save(wall)
            sync()
            with Image.open(target / 'background.png') as image:
                self.assertEqual(image.getpixel((0, 0)), (0, 0, 255))

    def test_permission_setup_uses_desktop_approval(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            with patch.object(greeter_sync.os, 'access', return_value=False), \
                    patch.object(greeter_sync, 'Path') as path, \
                    patch.object(greeter_sync.subprocess, 'run') as run:
                path.return_value.is_dir.return_value = True
                path.return_value.__str__.return_value = '/var/lib/rebos-greeter/theme'
                greeter_sync.configure(home)
                command = run.call_args_list[0].args[0]
                self.assertEqual(command[0], str(home / '.local/bin/assistant-sudo'))
                self.assertIn('--reason', command)
                self.assertEqual(command[-1], '/var/lib/rebos-greeter/theme')
                self.assertEqual(run.call_args_list[-1].args[0],
                                 ['systemctl', '--user', 'start', 'regreet-sync.service'])
