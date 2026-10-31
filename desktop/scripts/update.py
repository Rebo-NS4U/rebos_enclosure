#!/usr/bin/env python3
"""Update from the remote default branch while retaining installed preferences."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import tempfile

from deploy import install, verify

REPOSITORY = 'https://github.com/Rebo-NS4U/rebos_enclosure.git'


def run(*args):
    subprocess.run(args, check=True)


def apply_snapshot(snapshot, home, dry_run=False):
    payload = snapshot / 'desktop/payload'
    verify(payload)
    return install(payload, home, dry_run=dry_run, preserve_preferences=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=REPOSITORY, help='Git source (default: official GitHub repository)')
    parser.add_argument('--branch', help='Branch override; defaults to remote default branch')
    parser.add_argument('--files-only', action='store_true', help='Skip package upgrades')
    parser.add_argument('--no-aur', action='store_true', help='Skip installed AUR package upgrades')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and verify only; no installed files or packages change')
    args = parser.parse_args()
    home = Path.home()
    if os.geteuid() == 0:
        parser.error('Run as your normal desktop user, without sudo')
    for variable, relative in [('XDG_CONFIG_HOME', '.config'), ('XDG_CACHE_HOME', '.cache'),
                               ('XDG_DATA_HOME', '.local/share'), ('XDG_STATE_HOME', '.local/state')]:
        if os.environ.get(variable, str(home / relative)) != str(home / relative):
            parser.error('This desktop snapshot requires standard XDG paths under HOME')
    # Lock outside HOME so previews do not create installation state.
    with open(Path(tempfile.gettempdir()) / f'rebos-update-{os.getuid()}.lock', 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error('Another desktop update is running')
        with tempfile.TemporaryDirectory(prefix='rebos-update-') as temporary:
            snapshot = Path(temporary) / 'snapshot'
            command = ['git', 'clone', '--depth=1']
            if args.branch:
                command += ['--branch', args.branch]
            run(*command, '--', args.repository, str(snapshot))
            commit = subprocess.check_output(['git', '-C', str(snapshot), 'rev-parse', 'HEAD'], text=True).strip()
            print(f'Updating desktop to {commit}', flush=True)
            apply_snapshot(snapshot, home, dry_run=True)
            if args.dry_run:
                print('Would upgrade installed packages' if not args.files_only else 'Package upgrades skipped')
                return
            if not args.files_only:
                if not Path('/etc/arch-release').exists():
                    parser.error('Package upgrades require Arch Linux; use --files-only elsewhere')
                import shutil
                sudo = home / '.local/bin/assistant-sudo'
                if sudo.is_file():
                    run(str(sudo), '--reason',
                        'Upgrade installed system packages before updating the desktop',
                        '--', 'pacman', '-Syu')
                else:
                    run('sudo', 'pacman', '-Syu')
                helper = shutil.which('paru') or shutil.which('yay')
                if helper and not args.no_aur:
                    run(helper, '-Sua')
            backup = apply_snapshot(snapshot, home)
            print(f'Applied GitHub commit {commit}. Recovery backup: {backup}')
            print('Log out and back in to load the updated desktop. Package upgrades are not undone by file recovery.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Update stopped: {error}. Any deployment backup contains a recovery journal.')
