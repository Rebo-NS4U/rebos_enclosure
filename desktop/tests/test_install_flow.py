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
    entry['content']=Path(args[-2]).read_text()
with open(os.environ['INSTALL_COMMAND_LOG'],'a') as stream:
    stream.write(json.dumps(entry)+'\\n')
if name=='pacman' and args==['-Qq']:
    print('linux')
'''


class InstallFlowTests(unittest.TestCase):
    def test_nvidia_setup_uses_selected_plan_without_touching_real_system(self):
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
            args = ['bash', str(ROOT / 'install.sh'), '--yes', '--groups', 'none',
                    '--graphics', 'nvidia-open', '--kernel-headers', 'linux-headers',
                    '--hybrid', '--early-kms', '--no-login', '--keep-network',
                    '--no-bluetooth', '--no-power', '--monitors',
                    str(ROOT / 'desktop/examples/monitors.json')]
            result = subprocess.run(args, env=env, text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            entries = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertTrue(any(e['command'] == 'sudo' and 'nvidia-open-dkms' in e['args'] and
                                'linux-headers' in e['args'] for e in entries))
            copied = {e['args'][-1]: e['content'] for e in entries if 'content' in e}
            self.assertEqual(copied['/etc/modprobe.d/90-rebos-nvidia.conf'],
                             'options nvidia_drm modeset=1 fbdev=1\n')
            self.assertEqual(copied['/etc/mkinitcpio.conf.d/90-rebos-nvidia.conf'],
                             'MODULES+=(nvidia nvidia_modeset nvidia_uvm nvidia_drm)\n')
            self.assertTrue(any(e['command'] == 'sudo' and e['args'] == ['mkinitcpio', '-P'] for e in entries))
            self.assertFalse(any(e['command'] == 'sudo' and 'systemctl' in e['args'] for e in entries))
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


if __name__ == '__main__':
    unittest.main()
