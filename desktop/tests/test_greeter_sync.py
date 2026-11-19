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
            legacy = ('rebos-greeter-sync.path', 'rebos-greeter-sync.service',
                      'regreet-sync.path', 'regreet-sync.timer', 'regreet-sync.service')
            for name in legacy:
                (units / name).touch()
            timer = units / 'regreet-sync.timer'
            timer.unlink()
            timer.symlink_to(home / 'removed-timer-source')
            wants = units / 'timers.target.wants'
            wants.mkdir()
            (wants / timer.name).symlink_to(timer)
            replacement_link = wants / 'greeter-sync.timer'
            replacement_link.symlink_to(units / replacement_link.name)
            with patch.object(greeter_sync.os, 'access', return_value=True), \
                    patch.object(greeter_sync, 'Path') as path, \
                    patch.object(greeter_sync.subprocess, 'run') as run:
                path.return_value.is_dir.return_value = True
                greeter_sync.configure(home)
            commands = [call.args[0] for call in run.call_args_list]
            replacement = commands.index(['systemctl', '--user', 'enable', '--now',
                                          'greeter-sync.path', 'greeter-sync.timer'])
            for name in set(legacy) - {timer.name}:
                action = ['disable', '--now'] if name.endswith(('.path', '.timer')) else ['stop']
                self.assertLess(commands.index(['systemctl', '--user', *action, name]),
                                replacement)
            self.assertFalse(timer.is_symlink())
            self.assertFalse((wants / timer.name).is_symlink())
            self.assertTrue(replacement_link.is_symlink())

    def test_wallpaper_and_color_changes(self):
        script = runpy.run_path(str(ROOT.parent / 'system/bin/greeter-sync'))
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            cache, target = home / 'cache', home / 'theme'
            cache.mkdir()
            target.mkdir()
            wall = home / 'wall.png'
            Image.new('RGB', (16, 16), 'red').save(wall)
            (cache / 'wallpapers.json').write_text(json.dumps({'currentWall': str(wall)}))
            palette = cache / 'effective-palette.json'
            palette.write_text('{"primary":"#112233"}')
            sync = script['main']
            sync.__globals__.update(HOME=home, CACHE=cache, TARGET=target)
            sync()
            self.assertEqual(json.loads((target / 'quickshell.json').read_text())['palette']['primary'], '#112233')
            timestamp = (target / 'background.png').stat().st_mtime_ns
            sync()
            self.assertEqual(timestamp, (target / 'background.png').stat().st_mtime_ns)
            palette.write_text('{"primary":"#abcdef"}')
            sync()
            self.assertEqual(json.loads((target / 'quickshell.json').read_text())['palette']['primary'], '#abcdef')
            Image.new('RGB', (16, 16), 'blue').save(wall)
            sync()
            with Image.open(target / 'background.png') as image:
                self.assertEqual(image.getpixel((0, 0)), (0, 0, 255))

    def test_material_metrics_and_public_export(self):
        script = runpy.run_path(str(ROOT.parent / 'system/bin/greeter-sync'))
        import subprocess
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            cache, target = home / 'cache', home / 'theme'
            cache.mkdir()
            target.mkdir()
            theme = home / '.config/enclosure/shell/config/theme.json'
            theme.parent.mkdir(parents=True)
            theme.write_text(json.dumps({
                'roundness': 16, 'font': 'JetBrains Mono', 'fontSize': 14,
                'shellStyle': 'custom', 'ditherStrength': 37, 'shellTransparency': 22,
                'apiKey': 'never-publish',
                'srBg': {'gradient': [['primary', 0], ['#112233', 1]],
                         'gradientType': 'radial', 'opacity': 0.8,
                         'border': ['primary', 2], 'apiKey': 'never-publish'}
            }))
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
            exported = json.loads((target / 'quickshell.json').read_text())
            self.assertEqual(exported['metrics']['radius'], 16)
            self.assertEqual(exported['palette']['foreground'], '#112233')
            self.assertNotIn('opacity', exported['palette'])
            self.assertEqual(exported['material']['shellStyle'], 'custom')
            self.assertEqual(exported['material']['ditherStrength'], 37)
            self.assertEqual(exported['material']['srBg']['gradientType'], 'radial')
            self.assertEqual(exported['material']['srBg']['border'], ['primary', 2])
            self.assertNotIn('never-publish', (target / 'quickshell.json').read_text())
            bar = theme.with_name('bar.json')
            bar.write_text('{"use12hFormat":false,"privateSetting":"never-publish"}')
            state = {'currentWall': str(wall), 'tintEnabled': True}
            (cache / 'wallpapers.json').write_text(json.dumps(state))
            sync()
            exported = json.loads((target / 'quickshell.json').read_text())
            self.assertEqual(exported['display'], {'use12hFormat': False, 'tintEnabled': True})
            self.assertNotIn('never-publish', (target / 'quickshell.json').read_text())
            timestamp = (target / 'background.png').stat().st_mtime_ns
            theme.write_text('{"roundness":0,"font":"Unsafe; font","fontSize":18}')
            sync()
            self.assertEqual(json.loads((target / 'quickshell.json').read_text())['metrics']['radius'], 0)
            self.assertEqual(json.loads((target / 'quickshell.json').read_text())['metrics']['font'], 'JetBrains Mono')
            self.assertFalse((target / 'regreet.css').exists())
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
                                 ['systemctl', '--user', 'start', 'greeter-sync.service'])
