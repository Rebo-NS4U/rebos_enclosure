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
    def test_legacy_watchers_stop_before_replacement_starts(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            units = home / '.config/systemd/user'
            units.mkdir(parents=True)
            legacy = ('rebos-greeter-sync.path', 'rebos-greeter-sync.service')
            for name in legacy:
                (units / name).touch()
            with patch.object(greeter_sync.os, 'access', return_value=True), \
                    patch.object(greeter_sync, 'Path') as path, \
                    patch.object(greeter_sync.subprocess, 'run') as run:
                path.return_value.is_dir.return_value = True
                greeter_sync.configure(home)
            commands = [call.args[0] for call in run.call_args_list]
            replacement = commands.index(['systemctl', '--user', 'enable', '--now',
                                          'regreet-sync.path', 'regreet-sync.timer'])
            for name in legacy:
                action = ['disable', '--now'] if name.endswith('.path') else ['stop']
                self.assertLess(commands.index(['systemctl', '--user', *action, name]),
                                replacement)

    def test_wallpaper_and_color_changes(self):
        script = runpy.run_path(str(ROOT.parent / 'system/bin/regreet-sync'))
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

    def test_playground_metrics_and_css(self):
        script = runpy.run_path(str(ROOT.parent / 'system/bin/regreet-sync'))
        import subprocess
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            cache, target = home / 'cache', home / 'theme'
            cache.mkdir()
            target.mkdir()
            config = home / '.config/regreet-sync'
            config.mkdir(parents=True)
            (config / 'regreet.css.in').write_text(
                (ROOT.parent / 'system/greeter/regreet.css.in').read_text())
            theme = home / '.config/enclosure/shell/config/theme.json'
            theme.parent.mkdir(parents=True)
            theme.write_text('{"roundness":16,"font":"JetBrains Mono","fontSize":14}')
            wall = home / 'wall.png'
            Image.new('RGB', (16, 16), 'red').save(wall)
            (cache / 'wallpapers.json').write_text(json.dumps({'currentWall': str(wall)}))
            roles = ('background', 'overBackground', 'surfaceContainerLowest',
                     'surfaceContainer', 'surfaceContainerHigh', 'outlineVariant',
                     'primary', 'overPrimary', 'error')
            palette = {role: '#112233' for role in roles}
            palette['opacity'] = 0.82
            (cache / 'effective-palette.json').write_text(json.dumps(palette))
            sync = script['main']
            sync.__globals__.update(HOME=home, CACHE=cache, TARGET=target)
            sync()
            css = (target / 'regreet.css').read_text()
            self.assertIn('border-radius: 16px', css)
            self.assertIn('border-radius: 10px', css)
            self.assertIn('font-size: 14px', css)
            self.assertNotIn('{{', css)
            self.assertNotIn('glass-texture', css)
            # GTK parses CSS without mapping a window or connecting to greetd.
            parser = """import gi, sys
 gi.require_version('Gtk', '4.0')
 from gi.repository import Gtk
 errors = []
 provider = Gtk.CssProvider()
 provider.connect('parsing-error', lambda p, section, error: errors.append(str(error)))
 provider.load_from_path(sys.argv[1])
 if errors: raise SystemExit('\\n'.join(errors))
"""
            parser = '\n'.join(line[1:] if line.startswith(' ') else line for line in parser.splitlines())
            subprocess.run(['/usr/bin/python3', '-c', parser, str(target / 'regreet.css')], check=True)
            timestamp = (target / 'background.png').stat().st_mtime_ns
            theme.write_text('{"roundness":0,"font":"Unsafe; font","fontSize":18}')
            sync()
            css = (target / 'regreet.css').read_text()
            self.assertIn('border-radius: 0px', css)
            self.assertIn('font-size: 18px', css)
            self.assertIn('font-family: "JetBrains Mono"', css)
            self.assertEqual(timestamp, (target / 'background.png').stat().st_mtime_ns)

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
