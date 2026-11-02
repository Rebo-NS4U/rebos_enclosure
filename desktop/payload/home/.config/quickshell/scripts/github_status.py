#!/usr/bin/env python3
"""Read installed revision and compare it with the official GitHub default branch."""
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

REPOSITORY = 'https://github.com/Rebo-NS4U/rebos_enclosure'
API = 'https://api.github.com/repos/Rebo-NS4U/rebos_enclosure'


def git(checkout, *args):
    return subprocess.check_output(['git', '-C', str(checkout), *args], text=True,
                                   stderr=subprocess.PIPE, timeout=20).strip()


def request(path):
    req = urllib.request.Request(API + path, headers={'Accept': 'application/vnd.github+json',
                                                     'User-Agent': 'Rebos-Desktop'})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def linked_checkout(home):
    shell = (home / '.config/quickshell').resolve()
    suffix = Path('desktop/payload/home/.config/quickshell')
    if shell.parts[-len(suffix.parts):] == suffix.parts:
        checkout = shell.parents[len(suffix.parts) - 1]
        if (checkout / '.git').exists():
            return checkout
    return None


def installed(home):
    checkout = linked_checkout(home)
    if checkout is not None:
        origin = git(checkout, 'remote', 'get-url', 'origin')
        if origin.removesuffix('.git').rstrip('/') not in (
                REPOSITORY, 'git@github.com:Rebo-NS4U/rebos_enclosure'):
            raise ValueError('Installed checkout uses a different GitHub repository.')
        return git(checkout, 'rev-parse', 'HEAD'), bool(git(checkout, 'status', '--porcelain'))
    state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state'))
    record = state / 'rebos-desktop/source.json'
    if record.exists():
        data = json.loads(record.read_text())
        if data.get('repository') == REPOSITORY:
            return data['commit'], bool(data.get('dirty', False))
    raise ValueError('Installed revision is unknown. Reinstall or update from the official repository to record it.')


def check(home):
    result = {'status': 'unknown', 'message': 'Not checked', 'local': '', 'remote': '', 'dirty': False}
    try:
        result['local'], result['dirty'] = installed(home)
        repo = request('')
        branch = repo['default_branch']
        from urllib.parse import quote
        latest = request('/commits/' + quote(branch, safe=''))['sha']
        result['remote'] = latest
        if latest == result['local']:
            result.update(status='current', message='Up to date')
        else:
            try:
                comparison = request('/compare/' + result['local'] + '...' + latest)
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                # Unpublished local commits cannot be compared by GitHub.
                checkout = linked_checkout(home)
                try:
                    if checkout is None:
                        raise ValueError('No local Git history')
                    counts = git(checkout, 'rev-list', '--left-right', '--count',
                                 result['local'] + '...' + latest).split()
                    local_count, remote_count = map(int, counts)
                    relation = ('diverged' if local_count and remote_count else
                                'behind' if local_count else 'ahead')
                    comparison = {'status': relation, 'ahead_by': remote_count}
                except (OSError, ValueError, subprocess.SubprocessError):
                    result.update(status='unpublished', message='Installed revision is unavailable on GitHub')
                    return result
            status = comparison['status']
            if status == 'ahead':
                result.update(status='behind', message=f"Update available · {comparison['ahead_by']} commits behind")
            elif status == 'behind':
                result.update(status='ahead', message='Local version is ahead of GitHub')
            elif status == 'identical':
                result.update(status='current', message='Up to date')
            else:
                result.update(status='diverged', message='Local version has diverged from GitHub')
        if result['dirty']:
            result['message'] += ' · local changes'
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        result.update(status='error', message='Could not check for updates: ' + str(error))
    return result


if __name__ == '__main__':
    print(json.dumps(check(Path.home())))
