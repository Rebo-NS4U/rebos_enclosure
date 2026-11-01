"""Run the real installer while containing system mutations behind recording stubs."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
STUB = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
name=Path(sys.argv[0]).name
args=sys.argv[1:]
entry={'command':name,'args':args}
if name=='sudo' and args and args[0]=='install':
    source=Path(args[-2])
    if source.is_file():
        entry['size']=source.stat().st_size
        try:
            entry['content']=source.read_text()
        except UnicodeError:
            pass
with open(os.environ['INSTALL_COMMAND_LOG'],'a') as stream:
    stream.write(json.dumps(entry)+'\\n')
if name=='pacman' and args==['-Qq']:
    print('linux')
if name=='systemctl' and args==['list-unit-files','ly*','--state=enabled','--no-legend']:
    print('ly@tty2.service enabled enabled')
'''


class InstallFlowTests(unittest.TestCase):
    def test_nvidia_setup_uses_selected_plan_without_touching_real_system(self):
        self.run_install(login=False)

    def test_regreet_installs_assets_and_migrates_ly_without_restarting_services(self):
        self.run_install(login=True)

    def run_install(self, login):
        with tempfile.TemporaryDirectory(prefix='rebos-flow-test-') as tmp:
            base = Path(tmp)
            home = base / 'home'
            home.mkdir()
            commands = base / 'bin'
            commands.mkdir()
            stub = commands / 'record'
            stub.write_text(STUB)
            stub.chmod(0o755)
            for name in ('sudo', 'pacman', 'systemctl', 'mkinitcpio', 'xdg-user-dirs-update', 'xdg-mime', 'xdg-settings'):
                (commands / name).symlink_to(stub)
            log = base / 'commands.jsonl'
            env = dict(os.environ, HOME=str(home), PATH=str(commands) + ':' + os.environ['PATH'],
                       INSTALL_COMMAND_LOG=str(log), PYTHONDONTWRITEBYTECODE='1')
            for key in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_CACHE_HOME'):
                env.pop(key, None)
            args = ['bash', str(ROOT / 'install.sh'), '--local-snapshot', '--yes', '--groups', 'none',
                    '--graphics', 'nvidia-open', '--kernel-headers', 'linux-headers',
                    '--hybrid', '--early-kms', '--keep-network',
                    '--no-bluetooth', '--no-power', '--monitors',
                    str(ROOT / 'desktop/examples/monitors.json')]
            if not login:
                args.append('--no-login')
            result = subprocess.run(args, env=env, text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((home / '.config/quickshell/version').read_text().strip(),
                             (ROOT / 'desktop/payload/home/.config/quickshell/version').read_text().strip())
            for relative in ('code/rebos-assistant/shell.qml', 'code/anime-streamer/menu_client.py',
                             '.config/quickshell/AnimeMenu.qml', '.local/bin/ani-cli',
                             '.local/bin/rebos-assistant', '.local/bin/anime-streamer'):
                self.assertTrue((home / relative).is_file(), relative)
            media_service = (home / '.config/systemd/user/anime-streamer.service').read_text()
            self.assertIn(str(home / 'code/anime-streamer/backend_server.py'), media_service)
            self.assertNotIn('@HOME@', media_service)
            panel = (home / '.config/systemd/user/rebos-panel.service').read_text()
            self.assertIn('Environment=QS_DISABLE_FILE_WATCHER=1', panel)
            self.assertIn('Restart=on-failure', panel)
            self.assertTrue((home / '.config/quickshell/scripts/qt_screen_guard.cpp').is_file())
            niri_config = (home / '.config/niri/config.kdl').read_text()
            self.assertIn('niri-blur.kdl', niri_config)
            self.assertIn('namespace="rebos_shell-anime"', niri_config)
            bindings = (home / '.config/niri/keybindings-defaults.kdl').read_text()
            self.assertIn(f'"ipc" "-p" "{home}/.config/quickshell"', bindings)
            entries = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertTrue(any(e['command'] == 'sudo' and 'nvidia-open-dkms' in e['args'] and
                                'linux-headers' in e['args'] for e in entries))
            copied = {e['args'][-1]: e['content'] for e in entries if 'content' in e}
            self.assertEqual(copied['/etc/modprobe.d/90-rebos-nvidia.conf'],
                             'options nvidia_drm modeset=1 fbdev=1\n')
            self.assertEqual(copied['/etc/mkinitcpio.conf.d/90-rebos-nvidia.conf'],
                             'MODULES+=(nvidia nvidia_modeset nvidia_uvm nvidia_drm)\n')
            self.assertTrue(any(e['command'] == 'sudo' and e['args'] == ['mkinitcpio', '-P'] for e in entries))
            service_calls = [e['args'] for e in entries
                             if e['command'] == 'sudo' and e['args'][0] == 'systemctl']
            if login:
                self.assertEqual(service_calls, [
                    ['systemctl', 'disable', 'ly@tty2.service'],
                    ['systemctl', 'enable', 'getty@tty2.service'],
                    ['systemctl', 'disable', 'getty@tty1.service'],
                    ['systemctl', 'enable', 'greetd.service']])
                for name in ('config.toml', 'regreet.toml'):
                    self.assertEqual(copied['/etc/greetd/' + name],
                                     (ROOT / 'desktop/payload/system/greetd' / name).read_text())
                for name in ('layout', 'cage-cursor'):
                    self.assertTrue(any(e['args'] and e['args'][-1] == '/usr/local/lib/rebos-greeter/' + name + '.so'
                                        and e.get('size', 0) > 0 for e in entries))
                for name in ('regreet.css', 'background.png', 'glass-texture.png'):
                    self.assertTrue(any(e['args'] and e['args'][-1] == '/var/lib/rebos-greeter/theme/' + name
                                        and e.get('size', 0) > 0 for e in entries))
                package_call = next(e['args'] for e in entries if e['command'] == 'sudo'
                                    and e['args'][:2] == ['pacman', '-S'])
                self.assertTrue({'greetd', 'greetd-regreet', 'cage'} <= set(package_call))
                self.assertNotIn('ly', package_call)
            else:
                self.assertEqual(service_calls, [])
                self.assertFalse(any(e['args'][-1].startswith(('/etc/greetd/', '/usr/local/lib/rebos-greeter/',
                                                             '/var/lib/rebos-greeter/')) for e in entries if e['args']))
            launcher = home / '.local/bin/rebos-prime-run'
            self.assertTrue(launcher.exists())
            subprocess.run(['bash', '-n', str(launcher)], check=True)
            plan = json.loads((home / '.local/state/rebos-desktop/installation.json').read_text())
            self.assertEqual(plan['groups'], [])
            self.assertEqual(plan['graphics'], 'nvidia-open')
            self.assertIn('focus-at-startup', (home / '.config/niri/monitors.kdl').read_text())
            backup = next((home / '.local/state/rebos-desktop/backups').iterdir())
            restored = subprocess.run(['python3', str(ROOT / 'desktop/scripts/deploy.py'), '--restore', str(backup)],
                                      env=env, text=True, capture_output=True)
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertFalse((home / '.config/niri').exists())
            self.assertFalse(launcher.exists())
            self.assertFalse((home / 'code/rebos-assistant/shell.qml').exists())
            self.assertFalse((home / '.config/systemd/user/anime-streamer.service').exists())
            self.assertFalse((home / '.config/systemd/user/rebos-panel.service').exists())


if __name__ == '__main__':
    unittest.main()
