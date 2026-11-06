#!/usr/bin/env python3
"""Project-scoped GitHub controls for the Settings panel. No shell evaluation."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

import github_status as status


def run(*args, cwd=None, timeout=90, input=None):
    result = subprocess.run(args, cwd=cwd, input=input, capture_output=True, text=True,
                            timeout=timeout, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0',
                                                  'GIT_LITERAL_PATHSPECS': '1', 'GH_PROMPT_DISABLED': '1', 'GIT_OPTIONAL_LOCKS': '0'})
    if result.returncode:
        message = (result.stderr or result.stdout).strip()
        raise ValueError(message or f'{args[0]} exited with code {result.returncode}')
    return result.stdout.rstrip('\n')


def git(path, *args, **kwargs):
    return run('git', '-C', str(path), *args, **kwargs)


def repo_name(value):
    value = value.strip().rstrip('/').removesuffix('.git')
    for prefix in ('https://github.com/', 'ssh://git@github.com/', 'git@github.com:'):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value):
        raise ValueError('Use a GitHub owner/repository name or a GitHub HTTPS/SSH URL.')
    if any(part in ('.', '..') or part.startswith('-') for part in value.split('/')):
        raise ValueError('Invalid GitHub repository name.')
    return value


def checkout(value):
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise ValueError('Select an existing local project folder.')
    root = Path(git(path, 'rev-parse', '--show-toplevel')).resolve()
    if root != path:
        raise ValueError(f'Select the repository root: {root}')
    name = repo_name(git(path, 'remote', 'get-url', 'origin'))
    return path, name


def state_file():
    return Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'rebos-desktop/github-projects.json'


def saved_paths():
    try:
        data = json.loads(state_file().read_text())
        return [str(p) for p in data.get('paths', []) if isinstance(p, str)]
    except (OSError, ValueError, TypeError):
        return []


def remember(path):
    target = state_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    paths = sorted(set(saved_paths() + [str(path)]))
    with tempfile.NamedTemporaryFile(mode='w', dir=target.parent, delete=False) as temporary:
        json.dump({'paths': paths}, temporary)
        temporary.write('\n')
    os.replace(temporary.name, target)


def desktop_checkout(home):
    """Resolve copied installations without treating installed files as a checkout."""
    linked = status.linked_checkout(home)
    if linked:
        return linked
    for candidate in (home / 'code/rebos_enclosure', home / 'rebos_enclosure'):
        try:
            path, name = checkout(str(candidate))
            if name == 'Rebo-NS4U/rebos_enclosure':
                return path
        except (OSError, ValueError, subprocess.SubprocessError):
            continue
    return None


def catalog():
    home = Path.home()
    candidates = saved_paths()
    code = home / 'code'
    if code.is_dir():
        candidates += [str(p) for p in code.iterdir() if (p / '.git').exists()]
    linked = desktop_checkout(home)
    if linked:
        candidates.append(str(linked))
    projects = []
    seen = set()
    for candidate in candidates:
        try:
            path, name = checkout(candidate)
            if str(path) in seen:
                continue
            seen.add(str(path))
            projects.append({'path': str(path), 'repository': name,
                             'label': f'{name} · {path.name}'})
        except (OSError, ValueError, subprocess.SubprocessError):
            continue
    return {'ok': True, 'projects': sorted(projects, key=lambda p: p['label'].lower()),
            'github_cli': bool(shutil.which('gh')), 'desktop_path': str(linked or '')}


def api(name, endpoint):
    # gh supplies credentials internally; no tokens pass through the panel.
    if shutil.which('gh'):
        try:
            return json.loads(run('gh', 'api', f'repos/{name}{endpoint}', timeout=30))
        except ValueError as error:
            # Preserve the status checker's local-history fallback for commits
            # that have not been published to GitHub yet.
            if 'HTTP 404' in str(error):
                raise status.urllib.error.HTTPError('https://api.github.com/repos/' + name + endpoint,
                                                    404, 'Not found on GitHub', {}, None) from error
            raise
    request = status.urllib.request.Request('https://api.github.com/repos/' + name + endpoint,
                headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Rebos-Desktop'})
    with status.urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def changes(path):
    # Include each untracked file, rather than offering whole directories to stage.
    return status.changed_files(git(path, 'status', '--porcelain=v1', '-z', '--untracked-files=all'))


def inspect(value):
    path, name = checkout(value)
    result = status.check(Path.home(), checkout=path, repository='https://github.com/' + name,
                          api_request=lambda endpoint: api(name, endpoint))
    result['installation'] = 'Local project checkout'
    result['path'] = str(path)
    result['repository_name'] = name
    result['branches'] = git(path, 'for-each-ref', '--format=%(refname:short)', 'refs/heads').splitlines()
    result['all_changes'] = changes(path)
    result['staged'] = [p for p in git(path, 'diff', '--cached', '--no-renames', '--name-only', '-z').split('\0') if p]
    result['history'] = []
    try:
        history = git(path, 'log', '-8', '--format=%H%x00%s%x00%an%x00%cI')
    except ValueError:
        # Freshly cloned empty repositories can still stage and create a commit.
        if git(path, 'rev-list', '--all'):
            raise
        history = ''
        result.update(status='unborn', message='No commits yet. Stage files and create the first commit.',
                      branch=git(path, 'symbolic-ref', '--short', 'HEAD'))
    for line in history.splitlines():
        fields = line.split('\0')
        if len(fields) == 4:
            result['history'].append(dict(zip(('sha', 'title', 'author', 'date'), fields)))
    # Branch tracking is separate from comparison with GitHub's default branch.
    try:
        result['upstream'] = git(path, 'rev-parse', '--abbrev-ref', '@{upstream}')
    except ValueError:
        result['upstream'] = ''
    result.update(upstream_ahead=None, upstream_behind=None, outgoing_commits=[])
    if result['upstream']:
        try:
            behind, ahead = map(int, git(path, 'rev-list', '--left-right', '--count', '@{upstream}...HEAD').split())
            result.update(upstream_ahead=ahead, upstream_behind=behind)
            for line in git(path, 'log', '-8', '--format=%H%x00%s', '@{upstream}..HEAD').splitlines():
                fields = line.split('\0', 1)
                if len(fields) == 2:
                    result['outgoing_commits'].append({'sha': fields[0], 'title': fields[1]})
        except ValueError:
            pass  # The branch may have changed while inspecting it.
    result['ok'] = True
    return result


def review(value):
    """Read-only repository checks; never fetch or run project-provided code."""
    path, name = checkout(value)
    try:
        branch = git(path, 'symbolic-ref', '--quiet', '--short', 'HEAD')
    except ValueError:
        branch = 'Detached HEAD'
    entries = changes(path)
    conflicts = git(path, 'ls-files', '--unmerged')
    lines = [f'Repository: {name}', f'Folder: {path}', f'Branch: {branch}',
             f'Local files: {len(entries)} changed entries.',
             f'Storage: {shutil.disk_usage(path).free / 1024**3:.1f} GB free.']
    problems = bool(conflicts)
    lines.append('Merge conflicts: resolve unmerged files.' if conflicts else 'Merge conflicts: none.')
    for label, flags in [('Unstaged', []), ('Staged', ['--cached'])]:
        result = subprocess.run(['git', '-C', str(path), 'diff', '--no-ext-diff', '--no-textconv', '--check', *flags],
                                capture_output=True, text=True, timeout=30)
        if result.returncode not in (0, 2):
            raise ValueError(result.stderr.strip() or f'{label} check failed.')
        problems |= result.returncode != 0
        lines.append(f'{label} whitespace: ' + (result.stdout.strip() or 'passed.'))
    lines.extend(['', 'Read-only local checks only. Project tests were not run.',
                  'Remote comparisons elsewhere use the last fetched Git state. Fetch origin to refresh it.'])
    return {'ok': True, 'message': 'Repository checks found issues.' if problems else 'Repository checks passed.',
            'output': '\n'.join(lines), 'path': str(path), 'refresh': False,
            'issues': problems}


def selected_paths(path, data, staged_only=False):
    selected = data.get('files', [])
    if not isinstance(selected, list) or not selected or len(selected) > 500:
        raise ValueError('Select between 1 and 500 files.')
    available = set(p for p in git(path, 'diff', '--cached', '--no-renames', '--name-only', '-z').split('\0') if p)
    if not staged_only:
        available.update(item['path'] for item in changes(path))
    for item in selected:
        if not isinstance(item, str) or PurePosixPath(item).is_absolute() or '..' in PurePosixPath(item).parts:
            raise ValueError('Select files inside this repository.')
        if item not in available:
            raise ValueError('A selected file changed or is no longer available. Refresh the project.')
    return list(dict.fromkeys(selected))


def require_clean(path):
    if git(path, 'status', '--porcelain'):
        raise ValueError('Commit or preserve local changes before switching branches or pulling.')


def clone_project(data):
    name = repo_name(data.get('repository', ''))
    destination = Path(data.get('destination', '')).expanduser()
    if not data.get('destination') or not destination.is_absolute():
        raise ValueError('Choose an absolute destination folder, such as ~/code/project.')
    if destination.exists() or destination.is_symlink():
        raise ValueError('The destination already exists. Choose a new folder.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which('gh'):
        output = run('gh', 'repo', 'clone', name, str(destination), timeout=180)
    else:
        output = run('git', 'clone', '--', 'https://github.com/' + name + '.git', str(destination), timeout=180)
    path, _ = checkout(destination)
    remember(path)
    return {'ok': True, 'message': 'Repository cloned.', 'output': output, 'path': str(path)}


class ProjectAction:
    def __init__(self, data):
        self.data = data
        self.path, self.name = checkout(data.get('path', ''))

    def do_add(self):
        kind = self.data.get("action")
        path = self.path
        remember(path)
        output = 'Project added.'
        return {'ok': True, 'message': f'{kind.capitalize()} completed.', 'output': output[-10000:], 'path': str(path)}


    def do_review(self):
        path = self.path
        return review(str(path))


    def do_fetch(self):
        kind = self.data.get("action")
        path = self.path
        output = git(path, 'fetch', 'origin', timeout=120)
        return {'ok': True, 'message': f'{kind.capitalize()} completed.', 'output': output[-10000:], 'path': str(path)}


    def do_pull(self):
        kind = self.data.get("action")
        path = self.path
        require_clean(path)
        if not git(path, 'rev-parse', '--abbrev-ref', '@{upstream}').startswith('origin/'):
            raise ValueError('This branch must track origin before pulling.')
        output = git(path, '-c', 'pull.rebase=false', 'pull', '--ff-only', timeout=120)
        return {'ok': True, 'message': f'{kind.capitalize()} completed.', 'output': output[-10000:], 'path': str(path)}


    def do_switch(self):
        data = self.data
        kind = self.data.get("action")
        path = self.path
        require_clean(path)
        branch = data.get('branch', '').strip()
        if not branch or branch.startswith('-'):
            raise ValueError('Enter a valid branch name.')
        git(path, 'check-ref-format', '--branch', branch)
        output = git(path, 'switch', *(['-c'] if kind == 'branch' else []), branch)
        return {'ok': True, 'message': f'{kind.capitalize()} completed.', 'output': output[-10000:], 'path': str(path)}


    def do_diff(self):
        data = self.data
        path = self.path
        files = selected_paths(path, data)
        try:
            git(path, 'rev-parse', '--verify', 'HEAD')
            base = ['HEAD']
        except ValueError:
            base = ['--cached']
        output = git(path, 'diff', '--no-color', '--no-ext-diff', '--no-textconv', *base, '--', *files)
        untracked = [c['path'] for c in changes(path) if c['kind'] == 'Untracked' and c['path'] in files]
        if untracked:
            output += '\nUntracked files are not in the diff yet. Open them in your editor or stage them to review additions.\n' + '\n'.join(untracked)
        return {'ok': True, 'message': 'Selected file diff', 'output': output[:20000] or 'No differences.',
                'path': str(path), 'refresh': False}


    def do_stage(self):
        data = self.data
        kind = self.data.get("action")
        path = self.path
        files = selected_paths(path, data)
        output = git(path, 'add', '--', *files)
        return {'ok': True, 'message': f'{kind.capitalize()} completed.', 'output': output[-10000:], 'path': str(path)}


    def do_unstage(self):
        data = self.data
        kind = self.data.get("action")
        path = self.path
        output = git(path, 'restore', '--staged', '--', *selected_paths(path, data, staged_only=True))
        return {'ok': True, 'message': f'{kind.capitalize()} completed.', 'output': output[-10000:], 'path': str(path)}


    def do_commit(self):
        data = self.data
        kind = self.data.get("action")
        path = self.path
        files = selected_paths(path, data, staged_only=True)
        message = data.get('message', '').strip()
        if not message:
            raise ValueError('Enter a commit message.')
        if git(path, 'diff', '--name-only', '--', *files):
            raise ValueError('Selected files have newer unstaged edits. Stage them again before committing.')
        renames = iter(git(path, 'diff', '--cached', '--name-status', '-z', '--diff-filter=R').split('\0'))
        for entry in renames:
            if entry.startswith('R'):
                pair = {next(renames), next(renames)}
                if pair.intersection(files) and not pair.issubset(files):
                    raise ValueError('Select both the old and new paths for a staged rename.')
        output = git(path, 'commit', '--only', '-m', message, '--', *files)
        return {'ok': True, 'message': f'{kind.capitalize()} completed.', 'output': output[-10000:], 'path': str(path)}


    def do_push(self):
        kind = self.data.get("action")
        path = self.path
        name = self.name
        destinations = git(path, 'remote', 'get-url', '--push', '--all', 'origin').splitlines()
        if not destinations or any(repo_name(url) != name for url in destinations):
            raise ValueError('The push destination differs from the selected GitHub repository.')
        branch = git(path, 'symbolic-ref', '--quiet', '--short', 'HEAD')
        if branch.startswith('-'):
            raise ValueError('Unsupported branch name.')
        output = git(path, 'push', '--set-upstream', 'origin', f'HEAD:refs/heads/{branch}', timeout=120)
        return {'ok': True, 'message': f'{kind.capitalize()} completed.', 'output': output[-10000:], 'path': str(path)}


    def do_pr(self):
        data = self.data
        kind = self.data.get("action")
        path = self.path
        name = self.name
        title = data.get('title', '').strip()
        base = data.get('base', '').strip()
        if not title or not base or base.startswith('-'):
            raise ValueError('Enter a pull request title and base branch.')
        branch = git(path, 'symbolic-ref', '--quiet', '--short', 'HEAD')
        remote_sha = git(path, 'ls-remote', '--heads', 'origin', 'refs/heads/' + branch).split()
        if not remote_sha or remote_sha[0] != git(path, 'rev-parse', 'HEAD'):
            raise ValueError('Push this branch before creating a pull request.')
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md') as body:
            body.write(data.get('body', ''))
            body.flush()
            output = run('gh', 'pr', 'create', '--repo', name, '--head', branch,
                         '--base', base, '--title', title, '--body-file', body.name,
                         *(['--draft'] if data.get('draft', True) else []), cwd=path, timeout=90)
        return {'ok': True, 'message': f'{kind.capitalize()} completed.', 'output': output[-10000:], 'path': str(path)}


def action(data):
    kind = data.get('action')
    if kind == 'clone':
        return clone_project(data)
    command = ProjectAction(data)
    method = PROJECT_HANDLERS.get(kind)
    if method is None:
        raise ValueError('Unknown project action.')
    return getattr(command, method)()


PROJECT_HANDLERS = {'add': 'do_add', 'review': 'do_review', 'fetch': 'do_fetch', 'pull': 'do_pull', 'switch': 'do_switch', 'branch': 'do_switch', 'diff': 'do_diff', 'stage': 'do_stage', 'unstage': 'do_unstage', 'commit': 'do_commit', 'push': 'do_push', 'pr': 'do_pr'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['catalog', 'remote', 'inspect', 'action'])
    parser.add_argument('--path')
    args = parser.parse_args()
    try:
        if args.command == 'catalog':
            result = catalog()
        elif args.command == 'remote':
            result = {'ok': True, 'repositories': json.loads(run('gh', 'repo', 'list', '--limit', '100',
                '--json', 'nameWithOwner,isPrivate,url'))}
        elif args.command == 'inspect':
            # Copied desktops can also have a verified Enclosure checkout.
            # Inspect it for branch controls, falling back to the installed
            # revision only when no local checkout is available.
            path = args.path or desktop_checkout(Path.home())
            result = inspect(str(path)) if path else status.check(Path.home())
        else:
            result = action(json.loads(sys.stdin.readline()))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result = {'ok': False, 'message': str(error)}
    print(json.dumps(result))


if __name__ == '__main__':
    main()
