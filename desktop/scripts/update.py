#!/usr/bin/env python3
"""Update from the remote default branch or a release, retaining preferences."""
import argparse
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from deploy import SOURCE_ROOTS, install, verify
from update_health import validate
from linked_update import prepare

REPOSITORY = 'https://github.com/Rebo-NS4U/rebos_enclosure.git'
# Frozen bootstrap contract: old launchers pass one fetched payload and lock FD.
FETCHED_UPDATE_PROTOCOL = 1


def run(*args):
    subprocess.run(args, check=True)


def source_checkout(home):
    checkouts = set()
    for relative in SOURCE_ROOTS:
        path = home / relative
        if not path.is_symlink():
            continue
        target = path.resolve()
        suffix = Path('desktop/payload/home') / relative
        if tuple(target.parts[-len(suffix.parts):]) == suffix.parts:
            checkout = target.parents[len(suffix.parts) - 1]
            if not (checkout / '.git').exists():
                raise ValueError(f'Missing source checkout: {checkout}')
            checkouts.add(checkout)
    if len(checkouts) > 1:
        raise ValueError('Application links point to different checkouts')
    return next(iter(checkouts), None)


def apply_snapshot(snapshot, home, dry_run=False):
    payload = snapshot / 'desktop/payload'
    verify(payload)
    if dry_run:
        validate(payload)
    checkout = source_checkout(home)
    if checkout is not None:
        def git_output(*args):
            return subprocess.check_output(['git', '-C', str(checkout), *args], text=True).strip()
        incoming = subprocess.check_output(['git', '-C', str(snapshot), 'remote', 'get-url', 'origin'], text=True).strip()
        if git_output('remote', 'get-url', 'origin') != incoming:
            raise ValueError('Update repository differs from the linked checkout origin')
        with prepare(checkout, snapshot, home) as staged:
            if dry_run:
                validate(staged.plan / 'desktop/payload')
                print(f'Would update linked checkout and preserve local edits: {checkout}')
                return install(staged.plan / 'desktop/payload', home, dry_run=True,
                               preserve_preferences=True, link_source=True)
            staged.apply()
        return install(checkout / 'desktop/payload', home,
                       preserve_preferences=True, link_source=True)
    return install(payload, home, dry_run=dry_run, preserve_preferences=True)


def check_local_changes(home):
    record = home / '.local/state/rebos-desktop/source.json'
    if not record.is_file():
        return
    files = json.loads(record.read_text()).get('files', {})
    changed = []
    for relative, expected in files.items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe path in installed source record')
        destination = home / path
        if not destination.is_file() or hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
            changed.append(relative)
    if changed:
        raise ValueError('Installed managed files changed since deployment: '
                         + ', '.join(changed[:20])
                         + '. Save these fixes in the repository first. To replace them with the fetched snapshot '
                         'and retain a recovery backup, explicitly use --allow-local-changes')


def apply_fetched_snapshot(snapshot, home, args):
    if not args.allow_local_changes and source_checkout(home) is None:
        check_local_changes(home)
    commit = subprocess.check_output(['git', '-C', str(snapshot), 'rev-parse', 'HEAD'], text=True).strip()
    print(f'Updating desktop to {commit}', flush=True)
    apply_snapshot(snapshot, home, dry_run=True)
    if args.dry_run:
        print('Would upgrade installed packages' if not args.files_only else 'Package upgrades skipped')
        return
    if not args.files_only:
        if not Path('/etc/arch-release').exists():
            raise ValueError('Package upgrades require Arch Linux; use --files-only elsewhere')
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
    if not args.files_only:
        # Qt upgrades can change which QML properties and types are available.
        validate(snapshot / "desktop/payload")
    if not args.allow_local_changes and source_checkout(home) is None:
        check_local_changes(home)
    backup = apply_snapshot(snapshot, home)
    # Use the fetched implementation so this update matches its payload.
    greeter_setup = snapshot / 'desktop/scripts/greeter_sync.py'
    if greeter_setup.is_file():
        run('python3', str(greeter_setup))
    print(f'Applied GitHub commit {commit}. Recovery backup: {backup}')
    print('Log out and back in to load the updated desktop. Package upgrades are not undone by file recovery.')


def fetch_snapshot(snapshot, args, linked=None):
    if linked is not None:
        run('git', 'clone', '--shared', '--no-checkout', str(linked), str(snapshot))
        run('git', '-C', str(snapshot), 'remote', 'set-url', 'origin', args.repository)
        ref = ('refs/tags/' + args.release if args.release else
               'refs/heads/' + args.branch if args.branch else 'HEAD')
        run('git', '-C', str(snapshot), 'fetch', '--', args.repository, ref)
        run('git', '-C', str(snapshot), 'checkout', '--quiet', '--detach', 'FETCH_HEAD')
    elif args.release:
        print(f'Fetching desktop release: {args.release}', flush=True)
        run('git', 'init', '--quiet', str(snapshot))
        run('git', '-C', str(snapshot), 'remote', 'add', 'origin', args.repository)
        run('git', '-C', str(snapshot), 'fetch', '--depth=1', '--',
            args.repository, f'refs/tags/{args.release}')
        run('git', '-C', str(snapshot), 'checkout', '--quiet', '--detach', 'FETCH_HEAD')
    else:
        command = ['git', 'clone', '--depth=1']
        if args.branch:
            command += ['--branch', args.branch]
        run(*command, '--', args.repository, str(snapshot))


def supports_handoff(script):
    if not script.is_file():
        return False
    tree = ast.parse(script.read_bytes(), filename=str(script))
    for node in tree.body:
        if (isinstance(node, ast.Assign) and
                any(isinstance(target, ast.Name) and target.id == 'FETCHED_UPDATE_PROTOCOL'
                    for target in node.targets)):
            if isinstance(node.value, ast.Constant) and node.value.value == FETCHED_UPDATE_PROTOCOL:
                return True
            raise ValueError('Fetched updater uses an unsupported handoff protocol; refresh your launcher')
    return False



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=REPOSITORY, help='Git source (default: official GitHub repository)')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--branch', help='Branch override; defaults to remote default branch')
    source.add_argument('--release', help='Exact release tag, e.g. v1.3.1')
    parser.add_argument('--allow-local-changes', action='store_true',
                        help='Replace locally edited managed code after saving it in the recovery backup')
    parser.add_argument('--files-only', action='store_true', help='Skip package upgrades')
    parser.add_argument('--no-aur', action='store_true', help='Skip installed AUR package upgrades')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and verify only; no installed files or packages change')
    parser.add_argument('--fetched-snapshot', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--lock-fd', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.release is not None:
        if not args.release or args.release.startswith('-') or subprocess.run(
                ['git', 'check-ref-format', f'refs/tags/{args.release}'],
                capture_output=True).returncode:
            parser.error('Invalid release tag')
    home = Path.home()
    if os.geteuid() == 0:
        parser.error('Run as your normal desktop user, without sudo')
    for variable, relative in [('XDG_CONFIG_HOME', '.config'), ('XDG_CACHE_HOME', '.cache'),
                               ('XDG_DATA_HOME', '.local/share'), ('XDG_STATE_HOME', '.local/state')]:
        if os.environ.get(variable, str(home / relative)) != str(home / relative):
            parser.error('This desktop snapshot requires standard XDG paths under HOME')
    # The bootstrap keeps this same lock across the fresh Python subprocess.
    lock_path = Path(tempfile.gettempdir()) / f'rebos-update-{os.getuid()}.lock'
    if (args.fetched_snapshot is None) != (args.lock_fd is None):
        parser.error('Internal snapshot and lock must be provided together')
    if args.lock_fd is not None:
        stat = os.fstat(args.lock_fd)
        expected = lock_path.stat()
        if (stat.st_dev, stat.st_ino) != (expected.st_dev, expected.st_ino):
            parser.error('Invalid inherited updater lock')
    with (os.fdopen(args.lock_fd, 'a') if args.lock_fd is not None else open(lock_path, 'a')) as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error('Another desktop update is running')
        if args.fetched_snapshot is not None:
            snapshot = args.fetched_snapshot.resolve(strict=True)
            origin = subprocess.check_output(
                ['git', '-C', str(snapshot), 'remote', 'get-url', 'origin'], text=True).strip()
            if origin != args.repository:
                parser.error('Fetched payload origin differs from requested repository')
            apply_fetched_snapshot(snapshot, home, args)
            return
        with tempfile.TemporaryDirectory(prefix='rebos-update-') as temporary:
            # Always fetch the current controller, even for an older release.
            controller = Path(temporary) / 'controller'
            selectors = argparse.Namespace(repository=args.repository, release=None, branch=None)
            fetch_snapshot(controller, selectors, source_checkout(home))
            snapshot = controller
            if args.release or args.branch:
                snapshot = Path(temporary) / 'snapshot'
                fetch_snapshot(snapshot, args, source_checkout(home))
            script = controller / 'desktop/scripts/update.py'
            if supports_handoff(script):
                print('Using the freshly fetched updater.', flush=True)
                subprocess.run([sys.executable, str(script), *sys.argv[1:],
                                '--fetched-snapshot', str(snapshot),
                                '--lock-fd', str(lock.fileno())],
                               pass_fds=(lock.fileno(),), check=True)
            else:
                # Compatibility with releases published before protocol v1.
                # Never execute an old controller over the current one.
                print('Fetched source predates updater handoff; using the local compatible updater.', flush=True)
                apply_fetched_snapshot(snapshot, home, args)



if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, SyntaxError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Update stopped: {error}. Any deployment backup contains a recovery journal.')
