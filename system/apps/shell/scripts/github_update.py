#!/usr/bin/env python3
"""Interactive installed-desktop update launched by GitHub Settings."""
import argparse
from pathlib import Path
import subprocess
import sys

from github_projects import checkout


def update_command(path, packages=False):
    root, name = checkout(path)
    if name != 'Rebo-NS4U/rebos_enclosure':
        raise ValueError('Desktop updates require the official Rebos Enclosure checkout.')
    updater = root / 'update.sh'
    if not updater.is_file():
        raise ValueError('This checkout has no desktop updater.')
    return ['bash', str(updater)] + ([] if packages else ['--files-only'])


def perform(path, packages=False, run=subprocess.run, ask=input):
    command = update_command(path, packages)
    print('Previewing the latest official desktop update.', flush=True)
    print('Package upgrades: ' + ('included' if packages else 'skipped'), flush=True)
    result = run(command + ['--dry-run'])
    if result.returncode:
        print('Preview failed. Nothing was applied by this update action.', flush=True)
        return result.returncode
    print('\nApplying preserves personal preferences and creates a recovery backup.')
    print('Locally edited managed files may block the update; they are never overridden here.')
    print('The updater fetches the latest version again and verifies it before applying.')
    if ask('Type UPDATE to apply, or press Enter to cancel: ').strip() != 'UPDATE':
        print('Update cancelled.')
        return 0
    result = run(command)
    print('Update completed. Log out and back in when ready.' if result.returncode == 0
          else 'Update failed. Review the output above for errors and recovery information.', flush=True)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', required=True)
    parser.add_argument('--packages', action='store_true')
    args = parser.parse_args()
    code = 1
    try:
        code = perform(args.path, args.packages)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'Update stopped: {error}', flush=True)
    except (EOFError, KeyboardInterrupt):
        print('\nUpdate interrupted. Review any output above before retrying.', flush=True)
    try:
        input('\nPress Enter to close this window.')
    except (EOFError, KeyboardInterrupt):
        pass
    return code


if __name__ == '__main__':
    raise SystemExit(main())
