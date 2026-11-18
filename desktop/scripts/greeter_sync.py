"""Enable theme syncing for an installed Enclosure Quickshell greeter, without restarting it."""
import os
from pathlib import Path
import subprocess


def configure(home):
    theme = Path('/var/lib/rebos-greeter/theme')
    if not theme.is_dir():
        print('Quickshell greeter sync skipped: Enclosure greeter is not installed')
        return
    helper = home / '.local/bin/assistant-sudo'
    if not os.access(theme, os.W_OK) or any(
            not os.access(theme / name, os.W_OK)
            for name in ('quickshell.json', 'background.png')):
        subprocess.run([str(helper), '--reason',
                        'Enable automatic wallpaper and color updates for Quickshell greeter',
                        '--', '/usr/bin/chown', '-R', f'{os.getuid()}:{os.getgid()}', str(theme)],
                       check=True)
    # Older desktops used a separate exporter watching the same palette. Leaving
    # both enabled can race theme writes and exhaust the old unit's start limit.
    units = home / '.config/systemd/user'
    for name in ('rebos-greeter-sync.path', 'rebos-greeter-sync.service',
                 'regreet-sync.path', 'regreet-sync.timer', 'regreet-sync.service'):
        unit = units / name
        if unit.exists():
            action = ['disable', '--now'] if name.endswith(('.path', '.timer')) else ['stop']
            subprocess.run(['systemctl', '--user', *action, name], check=True)
        # The payload may already have removed the old unit's source file.
        unit.unlink(missing_ok=True)
        for directory in (*units.glob('*.wants'), *units.glob('*.requires')):
            link = directory / name
            if link.is_symlink():
                link.unlink()
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'enable', '--now',
                    'greeter-sync.path', 'greeter-sync.timer'], check=True)
    # A fresh update must render even if the cached signatures are unchanged.
    (home / '.cache/rebos_shell/greeter-sync.json').unlink(missing_ok=True)
    subprocess.run(['systemctl', '--user', 'start', 'greeter-sync.service'], check=True)
    print('Quickshell greeter now uses your current wallpaper and colors at the next login')


if __name__ == '__main__':
    configure(Path.home())
