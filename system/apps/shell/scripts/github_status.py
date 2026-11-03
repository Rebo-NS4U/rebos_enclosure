#!/usr/bin/env python3
"""Read installed revision and compare it with the official GitHub default branch."""
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.request
from urllib.parse import quote
from datetime import datetime, timezone

REPOSITORY = 'https://github.com/Rebo-NS4U/rebos_enclosure'
API = 'https://api.github.com/repos/Rebo-NS4U/rebos_enclosure'


def git(checkout, *args):
    return subprocess.check_output(['git', '-C', str(checkout), *args], text=True,
                                   stderr=subprocess.PIPE, timeout=20).rstrip('\n')


def request(path):
    req = urllib.request.Request(API + path, headers={'Accept': 'application/vnd.github+json',
                                                     'User-Agent': 'Rebos-Desktop'})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def linked_checkout(home):
    shell = (home / '.config/quickshell').resolve()
    for parent in shell.parents:
        if (parent / '.git').exists() and ((parent / 'system') in shell.parents or
                (parent / 'desktop/payload/home') in shell.parents):
            return parent
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


def commit_details(data):
    commit = data.get('commit', {})
    author = commit.get('author') or {}
    return {'sha': data.get('sha', ''),
            'title': commit.get('message', '').split('\n')[0],
            'author': author.get('name', ''), 'date': author.get('date', '')}


def changed_files(raw):
    """Parse NUL-delimited porcelain, including rename source records."""
    entries = iter(raw.split('\0'))
    files = []
    for entry in entries:
        if not entry:
            continue
        code, path = entry[:2], entry[3:]
        if 'R' in code or 'C' in code:
            next(entries, None)
        label = ('Untracked' if code == '??' else 'Renamed' if 'R' in code else
                 'Conflicted' if 'U' in code or code in ('AA', 'DD') else
                 'Deleted' if 'D' in code else 'Added' if 'A' in code else 'Modified')
        files.append({'path': path, 'kind': label})
    return files


def local_details(home, result, checkout=None):
    checkout = checkout or linked_checkout(home)
    result['installation'] = 'Linked source checkout' if checkout else 'Copied installation'
    if checkout is None:
        return
    result['branch'] = git(checkout, 'rev-parse', '--abbrev-ref', 'HEAD')
    if result['branch'] == 'HEAD':
        result['branch'] = 'Detached HEAD'
    fields = git(checkout, 'log', '-1', '--format=%s%x00%an%x00%cI').split('\0')
    if len(fields) == 3:
        result['local_commit'] = dict(zip(('title', 'author', 'date'), fields))
    changes = changed_files(git(checkout, 'status', '--porcelain=v1', '-z'))
    result['change_count'] = len(changes)
    result['changes'] = changes[:12]


def check(home, checkout=None, repository=REPOSITORY, api_request=None):
    result = {'status': 'unknown', 'message': 'Not checked', 'local': '', 'remote': '', 'dirty': False,
              'repository': repository, 'branch': '', 'default_branch': '',
              'installation': '', 'local_commit': {}, 'remote_commit': {},
              'ahead': None, 'behind': None, 'changes': [], 'change_count': None,
              'incoming': [], 'checked_at': datetime.now(timezone.utc).isoformat()}
    fetch = api_request or request
    try:
        if checkout is None:
            result['local'], result['dirty'] = installed(home)
        else:
            result['local'] = git(checkout, 'rev-parse', 'HEAD')
            result['dirty'] = bool(git(checkout, 'status', '--porcelain'))
        try:
            if checkout is None:
                local_details(home, result)
            else:
                local_details(home, result, checkout)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            result['details_error'] = 'Some local details are unavailable: ' + str(error)
        repo = fetch('')
        branch = repo['default_branch']
        result['default_branch'] = branch
        remote_commit = fetch('/commits/' + quote(branch, safe=''))
        latest = remote_commit['sha']
        result['remote_commit'] = commit_details(remote_commit)
        result['remote'] = latest
        if latest == result['local']:
            if not result['local_commit']:
                result['local_commit'] = result['remote_commit']
            result.update(status='current', message='Up to date', ahead=0, behind=0)
        else:
            try:
                comparison = fetch('/compare/' + result['local'] + '...' + latest)
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                error.close()
                # Unpublished local commits cannot be compared by GitHub.
                local_checkout = checkout or linked_checkout(home)
                try:
                    if local_checkout is None:
                        raise ValueError('No local Git history')
                    counts = git(local_checkout, 'rev-list', '--left-right', '--count',
                                 result['local'] + '...' + latest).split()
                    local_count, remote_count = map(int, counts)
                    relation = ('diverged' if local_count and remote_count else
                                'behind' if local_count else 'ahead')
                    comparison = {'status': relation, 'ahead_by': remote_count, 'behind_by': local_count}
                except (OSError, ValueError, subprocess.SubprocessError):
                    result.update(status='unpublished', message='Installed revision is unavailable on GitHub')
                    return result
            result['ahead'] = comparison.get('behind_by')
            result['behind'] = comparison.get('ahead_by')
            commits = comparison.get('commits', [])
            # GitHub caps unpaginated comparisons at 250 commits. Fetch the last
            # page for large updates so the list still contains recent commits.
            total = comparison.get('total_commits', len(commits))
            if total > 250:
                try:
                    page = (total + 4) // 5
                    commits = fetch('/compare/' + result['local'] + '...' + latest
                                      + '?per_page=5&page=' + str(page)).get('commits', [])
                except (OSError, ValueError, KeyError) as error:
                    commits = []
                    result['details_error'] = 'Incoming commit details are unavailable: ' + str(error)
            result['incoming'] = [commit_details(c) for c in commits[-5:][::-1]]
            status = comparison['status']
            if status == 'ahead':
                result.update(status='behind', message=f"Update available · {comparison['ahead_by']} commits behind")
            elif status == 'behind':
                result.update(status='ahead', message='Local version is ahead of GitHub')
            elif status == 'identical':
                result.update(status='current', message='Up to date', ahead=0, behind=0)
            else:
                result.update(status='diverged', message='Local version has diverged from GitHub')
        if result['dirty']:
            result['message'] += ' · local changes'
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        result.update(status='error', message='Could not check for updates: ' + str(error))
    return result


if __name__ == '__main__':
    print(json.dumps(check(Path.home())))
