#!/usr/bin/env python3
"""Enclosure development menu. Source, checks, deployment and Git stay separate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINS = {'https://github.com/Rebo-NS4U/rebos_enclosure',
           'git@github.com:Rebo-NS4U/rebos_enclosure'}


def run(args, root=ROOT, capture=False):
    return subprocess.run([str(a) for a in args], cwd=root, check=True,
                          text=True, stdout=subprocess.PIPE if capture else None,
                          env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})


def git(*args, root=ROOT, capture=False):
    result = run(['git', *args], root, capture)
    return result.stdout.strip() if capture else result


def verify_checkout(root=ROOT):
    actual = Path(git('rev-parse', '--show-toplevel', root=root, capture=True)).resolve()
    origin = git('remote', 'get-url', 'origin', root=root, capture=True).rstrip('/').removesuffix('.git')
    if actual != root.resolve() or origin not in ORIGINS:
        raise ValueError('Use the Enclosure checkout with its official origin; refusing another repository.')
    push_origins = git('remote', 'get-url', '--push', '--all', 'origin', root=root, capture=True).splitlines()
    if not push_origins or any(url.rstrip('/').removesuffix('.git') not in ORIGINS for url in push_origins):
        raise ValueError('Origin push destination must also be the official Enclosure repository.')
    return git('symbolic-ref', '--quiet', '--short', 'HEAD', root=root, capture=True)


def refresh_checksums(root=ROOT):
    """Hash only explicitly tracked payload files; never capture a live home."""
    payload = root / 'desktop/payload'
    names = git('ls-files', '-z', '--', 'desktop/payload', root=root, capture=True).split('\0')
    hashes = {}
    for name in filter(None, names):
        path = root / name
        relative = path.relative_to(payload).as_posix()
        if relative == 'checksums.json':
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError('Tracked payload file missing or symlinked: ' + relative)
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    # Fail before writing if untracked files would invalidate the deployer inventory.
    actual = {p.relative_to(payload).as_posix() for p in payload.rglob('*')
              if p.is_file() and p.name != 'checksums.json' and '__pycache__' not in p.parts}
    if actual != set(hashes):
        raise ValueError('Payload inventory differs from Git. Review and explicitly stage new/removed files first: ' +
                         ', '.join(sorted(actual ^ set(hashes))))
    (payload / 'checksums.json').write_text(json.dumps(dict(sorted(hashes.items())), indent=2) + '\n')
    run([sys.executable, 'desktop/scripts/deploy.py', '--verify'], root)


def checks(root=ROOT):
    git('diff', '--check', root=root)
    git('diff', '--cached', '--check', root=root)
    test_source(root)


def test_source(root):
    # Tests must not resolve the developer's running desktop or touch account state.
    with tempfile.TemporaryDirectory(prefix='enclosure-test-home-') as home:
        env = {**os.environ, 'HOME': home, 'PYTHONDONTWRITEBYTECODE': '1'}
        for key in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_CACHE_HOME'):
            env.pop(key, None)
        for command in ([sys.executable, 'desktop/scripts/deploy.py', '--verify'],
                        [sys.executable, '-m', 'unittest', 'discover', '-s', 'desktop/tests', '-p', 'test_*.py']):
            subprocess.run(command, cwd=root, check=True, env=env)


def stage(paths, root=ROOT):
    if not paths:
        raise ValueError('Specify the files to stage; the menu never stages the whole checkout.')
    for name in paths:
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or name in ('.', './', ''):
            raise ValueError('Choose explicit repository-relative file paths.')
        if (root / path).is_dir() or any(c in name for c in '*?['):
            raise ValueError('Stage files individually, without directories or wildcards.')
    git('--literal-pathspecs', 'add', '--', *paths, root=root)


def commit(message, root=ROOT):
    if not message or not message.strip():
        raise ValueError('A commit message is required.')
    if not git('diff', '--cached', '--name-only', root=root, capture=True):
        raise ValueError('No staged changes. Review and stage explicit files first.')
    tree = git('write-tree', root=root, capture=True)
    # Check the exact index export, not a working tree containing other edits.
    # checkout-index leaves .git out, so tests see the same source as the commit.
    with tempfile.TemporaryDirectory(prefix='enclosure-check-') as tmp:
        git('checkout-index', '--all', '--prefix=' + tmp + '/', root=root)
        export = Path(tmp)
        test_source(export)
    if git('write-tree', root=root, capture=True) != tree:
        raise ValueError('Staged files changed during verification. Review them and run commit again.')
    git('diff', '--cached', '--check', root=root)
    git('diff', '--cached', '--stat', root=root)
    git('commit', '-m', message, root=root)


def push(root=ROOT):
    branch = verify_checkout(root)
    remote = git('config', '--get', f'branch.{branch}.remote', root=root, capture=True)
    target = git('config', '--get', f'branch.{branch}.merge', root=root, capture=True)
    if remote != 'origin' or not target.startswith('refs/heads/'):
        raise ValueError('Configure an origin branch upstream before pushing.')
    # Ignore push.default and remote.push refspecs: push this branch only.
    git('push', 'origin', 'HEAD:' + target, root=root)


def action(name, args, root=ROOT):
    verify_checkout(root)
    if name == 'status':
        git('status', '--short', '--branch', root=root)
        git('log', '-5', '--oneline', root=root)
    elif name == 'diff':
        git('--no-pager', 'diff', root=root)
        git('--no-pager', 'diff', '--cached', root=root)
    elif name == 'check':
        checks(root)
    elif name == 'hashes':
        refresh_checksums(root)
    elif name == 'stage':
        stage(args.paths, root)
    elif name == 'commit':
        commit(args.message, root)
    elif name == 'push':
        push(root)
    elif name == 'pull':
        if git('status', '--porcelain', root=root, capture=True):
            raise ValueError('Commit or preserve local changes before pulling.')
        branch = verify_checkout(root)
        remote = git('config', '--get', f'branch.{branch}.remote', root=root, capture=True)
        target = git('config', '--get', f'branch.{branch}.merge', root=root, capture=True)
        if remote != 'origin' or not target.startswith('refs/heads/'):
            raise ValueError('Configure an origin branch upstream before pulling.')
        git('pull', '--ff-only', 'origin', target, root=root)
    elif name in ('preview', 'deploy'):
        command = [sys.executable, 'desktop/scripts/deploy.py', '--preserve-preferences']
        if name == 'preview':
            command += ['--dry-run']
        linked = False
        for relative in ('.config/quickshell', 'code/rebos-assistant', 'code/anime-streamer'):
            installed = Path.home() / relative
            if installed.is_symlink() and 'desktop/payload/home' in str(installed.resolve()):
                if installed.resolve() != (root / 'desktop/payload/home' / relative).resolve():
                    raise ValueError('Installed source links point to another checkout; use its menu.')
                linked = True
        if args.link_source or linked:
            command += ['--link-source']
        run(command, root)
    elif name == 'hardware':
        plan = run([sys.executable, 'desktop/scripts/setup.py', 'plan', '--machine', args.machine,
                    '--profile', 'core', '--groups', 'none'], root, capture=True).stdout
        subprocess.run([sys.executable, 'desktop/scripts/setup.py', 'summary'], input=plan,
                       cwd=root, text=True, check=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    elif name in ('update-preview', 'update'):
        run(['bash', 'update.sh', '--files-only'] + (['--dry-run'] if name == 'update-preview' else []), root)


MENU = [('status', 'Repository status'), ('diff', 'Review changes'),
        ('hardware', 'Detect hardware and preview machine plan'),
        ('check', 'Verify payload and run tests'), ('stage', 'Stage selected files'),
        ('hashes', 'Rebuild payload checksums from reviewed Git files'),
        ('preview', 'Preview local deployment'), ('deploy', 'Deploy local files (keep preferences)'),
        ('commit', 'Test staged source and commit'), ('push', 'Push committed changes to GitHub'),
        ('pull', 'Pull source updates (fast-forward only)'),
        ('update-preview', 'Preview installed desktop update from GitHub'),
        ('update', 'Update installed desktop from GitHub (files only)')]


def menu(args):
    branch = verify_checkout()
    while True:
        print(f'\nEnclosure Development — {branch}\n{ROOT}')
        for index, (_, label) in enumerate(MENU, 1):
            print(f'  {index:2}) {label}')
        selected = input('Choose a number, or q to quit: ').strip()
        if selected.lower() in ('q', 'quit'):
            return
        if not selected.isdigit() or not 1 <= int(selected) <= len(MENU):
            continue
        name = MENU[int(selected) - 1][0]
        try:
            if name == 'stage':
                args.paths = shlex.split(input('Repository-relative files (quote spaces): '))
            if name == 'commit':
                git('diff', '--cached', '--stat')
                args.message = input('Commit message (empty cancels): ')
                if not args.message.strip():
                    continue
            if name in ('push', 'pull', 'deploy', 'update'):
                if name == 'push':
                    git('log', '--oneline', '@{upstream}..HEAD')
                if name == 'deploy':
                    action('preview', args)
                if name == 'update':
                    action('update-preview', args)
                if input(f'Run {name}? Type yes: ').strip() != 'yes':
                    continue
            action(name, args)
            print('Completed: ' + name)
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            print('Action failed: ' + str(error), file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=[n for n, _ in MENU], help='Omit to open the menu')
    parser.add_argument('paths', nargs='*', help='Explicit files for stage')
    parser.add_argument('-m', '--message', help='Commit message')
    parser.add_argument('--machine', choices=('auto', 'desktop', 'laptop', 'virtual'), default='auto')
    parser.add_argument('--link-source', action='store_true', help='Opt into source links when deploying')
    args = parser.parse_args()
    if args.action:
        action(args.action, args)
    elif not sys.stdin.isatty():
        parser.error('The menu needs a terminal; specify an action for scripts.')
    else:
        menu(args)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit('Development action failed: ' + str(error))
    except (EOFError, KeyboardInterrupt):
        sys.exit(130)
