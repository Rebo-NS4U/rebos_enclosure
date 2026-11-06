#!/usr/bin/env python3
"""Enclosure development menu. Source, checks, deployment and Git stay separate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import inventory, manifest, source as source_path, checkout_for

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
    if manifest(payload).get('layout') == 2:
        actual = inventory(payload)
        tracked = set(git('ls-files', '-z', '--', 'config', 'system',
                          'desktop/payload/manifest.json', root=root, capture=True).split('\0'))
        names = {name if name != 'manifest.json' else 'desktop/payload/manifest.json' for name in actual}
        if names != tracked - {''}:
            raise ValueError('Payload inventory differs from Git. Review and explicitly stage new/removed files first.')
        hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in actual.items()}
        if any(path.is_symlink() for path in actual.values()):
            raise ValueError('Shipped source must not be symlinked.')
    else:
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


def outgoing(root=ROOT):
    """Use the same explicit destination as push, not push.default or another upstream."""
    branch = verify_checkout(root)
    try:
        remote = git('config', '--get', f'branch.{branch}.remote', root=root, capture=True)
        target = git('config', '--get', f'branch.{branch}.merge', root=root, capture=True)
        if remote != 'origin' or not target.startswith('refs/heads/'):
            return 'Push is not set up. Choose an origin branch before publishing.'
        destination = 'origin/' + target.removeprefix('refs/heads/')
        reference = 'refs/remotes/' + destination
        git('rev-parse', '--verify', '--quiet', reference, root=root, capture=True)
    except subprocess.CalledProcessError:
        return 'Push comparison unavailable. Set up the origin branch and fetch it first.'
    commits = git('log', '--reverse', '--format=%h  %s', reference + '..HEAD',
                  root=root, capture=True).splitlines()
    behind = int(git('rev-list', '--count', 'HEAD..' + reference, root=root, capture=True))
    lines = [f'Commits waiting to be pushed to {destination}: {len(commits)}',
             'Compared with the last fetched GitHub state; GitHub may have changed.']
    if behind:
        lines.append(f'GitHub has {behind} commits missing here. Update before pushing.')
    lines.extend(commits or ['No local commits waiting to be pushed.'])
    return '\n'.join(lines)


def health_report(root=ROOT):
    lines = ['System condition — read-only snapshot']
    disk = shutil.disk_usage(root)
    free = disk.free / 1024**3
    lines.append(f'Storage: {free:.1f} GB free where the project is stored. ' +
                 ('Space is running low.' if disk.free / disk.total < .1 or free < 2 else 'Enough free space.'))
    try:
        memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
        available = int(memory['MemAvailable'].split()[0])
        total = int(memory['MemTotal'].split()[0])
        lines.append(f'Memory: {available / 1024**2:.1f} GB available of {total / 1024**2:.1f} GB. ' +
                     ('Memory is running low.' if available / total < .1 else 'Memory has room.'))
    except (OSError, KeyError, ValueError):
        lines.append('Memory: could not read the current usage.')
    for label, flags in [('System services', []), ('Desktop user services', ['--user'])]:
        try:
            result = subprocess.run(['systemctl', *flags, '--failed', '--no-legend', '--plain', '--no-pager'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode:
                lines.append(label + ': could not check; service connection unavailable.')
            else:
                failed = [line.split()[0] for line in result.stdout.splitlines() if line.strip()]
                lines.append(label + (': failures reported — ' + ', '.join(failed) if failed else
                                      ': no failed services reported.'))
        except (OSError, subprocess.TimeoutExpired):
            lines.append(label + ': could not check right now.')
    changed = git('status', '--porcelain', '-z', root=root, capture=True)
    lines.append('Local files: changes have not all been saved in commits.' if changed else
                 'Local files: all changes are saved in commits.')
    lines.extend(['', outgoing(root), '',
                  'Project tests are separate from these live system readings.'])
    return '\n'.join(lines)


def push(root=ROOT):
    branch = verify_checkout(root)
    remote = git('config', '--get', f'branch.{branch}.remote', root=root, capture=True)
    target = git('config', '--get', f'branch.{branch}.merge', root=root, capture=True)
    if remote != 'origin' or not target.startswith('refs/heads/'):
        raise ValueError('Configure an origin branch upstream before pushing.')
    # Ignore push.default and remote.push refspecs: push this branch only.
    git('push', 'origin', 'HEAD:' + target, root=root)


class DevelopmentCommand:
    def __init__(self, name, args, root):
        self.name, self.args, self.root = name, args, root

    def do_status(self):
        root = self.root
        git('status', '--short', '--branch', root=root)
        git('log', '-5', '--oneline', root=root)
        print(outgoing(root))


    def do_outgoing(self):
        root = self.root
        print(outgoing(root))


    def do_health(self):
        root = self.root
        print(health_report(root))


    def do_diff(self):
        root = self.root
        git('--no-pager', 'diff', root=root)
        git('--no-pager', 'diff', '--cached', root=root)


    def do_check(self):
        root = self.root
        checks(root)


    def do_hashes(self):
        root = self.root
        refresh_checksums(root)


    def do_stage(self):
        args = self.args
        root = self.root
        stage(args.paths, root)


    def do_commit(self):
        args = self.args
        root = self.root
        commit(args.message, root)


    def do_push(self):
        root = self.root
        push(root)


    def do_pull(self):
        root = self.root
        if git('status', '--porcelain', root=root, capture=True):
            raise ValueError('Commit or preserve local changes before pulling.')
        branch = verify_checkout(root)
        remote = git('config', '--get', f'branch.{branch}.remote', root=root, capture=True)
        target = git('config', '--get', f'branch.{branch}.merge', root=root, capture=True)
        if remote != 'origin' or not target.startswith('refs/heads/'):
            raise ValueError('Configure an origin branch upstream before pulling.')
        git('pull', '--ff-only', 'origin', target, root=root)


    def do_preview(self):
        name = self.name
        args = self.args
        root = self.root
        command = [sys.executable, 'desktop/scripts/deploy.py', '--preserve-preferences']
        if name == 'preview':
            command += ['--dry-run']
        linked = False
        for relative in ('.config/quickshell', 'code/rebos-assistant', 'code/anime-streamer'):
            installed = Path.home() / relative
            if installed.is_symlink() and checkout_for(installed) is not None:
                if installed.resolve() != source_path(root / 'desktop/payload', relative).resolve():
                    raise ValueError('Installed source links point to another checkout; use its menu.')
                linked = True
        if args.link_source or linked:
            command += ['--link-source']
        run(command, root)


    def do_hardware(self):
        args = self.args
        root = self.root
        plan = run([sys.executable, 'desktop/scripts/setup.py', 'plan', '--machine', args.machine,
                    '--profile', 'core', '--groups', 'none'], root, capture=True).stdout
        subprocess.run([sys.executable, 'desktop/scripts/setup.py', 'summary'], input=plan,
                       cwd=root, text=True, check=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})


    def do_organize_preview(self):
        name = self.name
        root = self.root
        run([sys.executable, 'desktop/scripts/organize.py'] + (['--apply'] if name == 'organize' else []), root)


    def do_configs(self):
        root = self.root
        run(['xdg-open', str(Path.home() / '.config/enclosure')], root)


    def do_update_preview(self):
        name = self.name
        root = self.root
        run(['bash', 'update.sh', '--files-only'] + (['--dry-run'] if name == 'update-preview' else []), root)


def action(name, args, root=ROOT):
    verify_checkout(root)
    command = DevelopmentCommand(name, args, root)
    method = DEVELOPMENT_HANDLERS.get(name)
    if method is not None:
        getattr(command, method)()


DEVELOPMENT_HANDLERS = {'status': 'do_status', 'outgoing': 'do_outgoing', 'health': 'do_health', 'diff': 'do_diff', 'check': 'do_check', 'hashes': 'do_hashes', 'stage': 'do_stage', 'commit': 'do_commit', 'push': 'do_push', 'pull': 'do_pull', 'preview': 'do_preview', 'deploy': 'do_preview', 'hardware': 'do_hardware', 'organize-preview': 'do_organize_preview', 'organize': 'do_organize_preview', 'configs': 'do_configs', 'update-preview': 'do_update_preview', 'update': 'do_update_preview'}


MENU = [('health', 'System condition in plain words'),
        ('outgoing', 'Show commits waiting to be pushed'), ('configs', 'Open personal configuration folder'),
        ('organize-preview', 'Preview grouping installed settings and system files'),
        ('organize', 'Group installed settings and system files'),
        ('status', 'Repository status'), ('diff', 'Review changes'),
        ('hardware', 'Detect hardware and preview machine plan'),
        ('check', 'Verify payload and run tests'), ('stage', 'Stage selected files'),
        ('hashes', 'Rebuild payload checksums from reviewed Git files'),
        ('preview', 'Preview local deployment'), ('deploy', 'Deploy local files (keep preferences)'),
        ('commit', 'Test staged source and commit'), ('push', 'Push committed changes to GitHub'),
        ('pull', 'Pull source updates (fast-forward only)'),
        ('update-preview', 'Preview installed desktop update from GitHub'),
        ('update', 'Update installed desktop from GitHub (files only)')]


def prepare_menu_action(name, args):
    if name == 'stage':
        args.paths = shlex.split(input('Repository-relative files (quote spaces): '))
    if name == 'commit':
        git('diff', '--cached', '--stat')
        args.message = input('Commit message (empty cancels): ')
        if not args.message.strip():
            return False
    if name in ('push', 'pull', 'deploy', 'update', 'organize'):
        if name == 'push':
            print(outgoing())
        if name == 'organize':
            action('organize-preview', args)
        if name == 'deploy':
            action('preview', args)
        if name == 'update':
            action('update-preview', args)
        if input(f'Run {name}? Type yes: ').strip() != 'yes':
            return False
    return True


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
            if not prepare_menu_action(name, args):
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
