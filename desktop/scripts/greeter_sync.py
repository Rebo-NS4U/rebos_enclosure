"""Enable theme syncing for an installed Enclosure ReGreet, without restarting it."""
import os
from pathlib import Path
import subprocess


def configure(home):
    theme = Path('/var/lib/rebos-greeter/theme')
    if not theme.is_dir():
        print('ReGreet sync skipped: Enclosure greeter is not installed')
        return
    helper = home / '.local/bin/assistant-sudo'
    if not os.access(theme, os.W_OK) or any(
            not os.access(theme / name, os.W_OK)
            for name in ('regreet.css', 'background.png')):
        subprocess.run([str(helper), '--reason',
                        'Enable automatic wallpaper and color updates for ReGreet',
                        '--', '/usr/bin/chown', '-R', f'{os.getuid()}:{os.getgid()}', str(theme)],
                       check=True)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    # Older desktops used a separate exporter watching the same palette. Leaving
    # both enabled can race theme writes and exhaust the old unit's start limit.
    for name in ('rebos-greeter-sync.path', 'rebos-greeter-sync.service'):
        if (home / '.config/systemd/user' / name).exists():
            action = ['disable', '--now'] if name.endswith('.path') else ['stop']
            subprocess.run(['systemctl', '--user', *action, name], check=True)
    subprocess.run(['systemctl', '--user', 'enable', '--now',
                    'regreet-sync.path', 'regreet-sync.timer'], check=True)
    # A fresh update must render even if the cached signatures are unchanged.
    (home / '.cache/rebos_shell/regreet-sync.json').unlink(missing_ok=True)
    subprocess.run(['systemctl', '--user', 'start', 'regreet-sync.service'], check=True)
    print('ReGreet now uses your current wallpaper and colors at the next login')


if __name__ == '__main__':
    configure(Path.home())
