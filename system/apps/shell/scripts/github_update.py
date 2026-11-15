#!/usr/bin/env python3
"""Check published releases and apply a selected desktop release with progress."""
from console_helpers import close_console
import argparse
import json
from pathlib import Path
import subprocess
import urllib.error
from urllib.parse import quote

from github_projects import checkout, desktop_checkout
import github_status as status


def release_status():
    """Offer only a stable release that descends from the installed revision."""
    local, _ = status.installed(Path.home())
    try:
        release = status.request('/releases/latest')
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        error.close()
        return dict(available=False)
    if release.get('draft') or release.get('prerelease'):
        return dict(available=False)
    tag = release['tag_name']
    revision = status.request('/commits/' + quote(tag, safe=''))['sha']
    result = dict(local=local)
    if revision == local:
        return dict(available=False, tag=tag)
    status.compare_remote(status.request, result, Path.home(), None, revision)
    return dict(available=result.get('status') == 'behind', tag=tag)


def update_command(path, release=None):
    root, name = checkout(path)
    if name != 'Rebo-NS4U/rebos_enclosure':
        raise ValueError('Desktop updates require the official Rebos Enclosure checkout.')
    updater = root / 'update.sh'
    if not updater.is_file():
        raise ValueError('This checkout has no desktop updater.')
    if release is not None and (not release or release.startswith('-')):
        raise ValueError('A published release tag is required.')
    return ['bash', str(updater), '--files-only'] + (['--release', release] if release else ['--branch', 'main'])


def perform(path, release=None, run=subprocess.run):
    if release:
        latest = release_status()
        if not latest.get('available') or latest.get('tag') != release:
            raise ValueError('This release is no longer an available update. Check for updates again.')
    command = update_command(path, release)
    print('Installing Enclosure ' + (release or 'main') + '. Personal preferences are preserved.', flush=True)
    print('Verifying files and creating recovery backups before replacement.', flush=True)
    result = run(command)
    print('Update completed. Log out and back in when ready.' if result.returncode == 0
          else 'Update failed. Review the output above for errors and recovery information.', flush=True)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--path')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--release')
    selection.add_argument('--regular', action='store_true')
    args = parser.parse_args()
    code = 1
    try:
        if args.check:
            print(json.dumps(release_status()))
            return 0
        if not args.release and not args.regular:
            parser.error('--release or --regular is required when applying an update')
        path = args.path or desktop_checkout(Path.home())
        if not path:
            raise ValueError('No official Enclosure checkout is available.')
        code = perform(str(path), args.release)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        if args.check:
            print(json.dumps(dict(available=False, error=str(error))))
            return 1
        print(f'Update stopped: {error}', flush=True)
    except (EOFError, KeyboardInterrupt):
        print('\nUpdate interrupted. Review any output above before retrying.', flush=True)
    return close_console(code)


if __name__ == '__main__':
    raise SystemExit(main())
