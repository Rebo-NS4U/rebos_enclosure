#!/usr/bin/env python3
"""Refresh the selected desktop snapshot and publish it with ordinary Git."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timezone

from snapshot import build

REPO = Path(__file__).resolve().parents[2]


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def validate(payload, home):
    hashes = json.loads((payload / 'checksums.json').read_text())
    actual = {str(p.relative_to(payload)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in payload.rglob('*') if p.is_file() and p.name != 'checksums.json'}
    if hashes != actual:
        raise ValueError('Snapshot checksums do not match; nothing was published.')
    # The recipe is an explicit allowlist. Check forbidden user state as well.
    forbidden = {'.git', '.ssh', '.aws', '.codex', 'auth.json', '.env',
                 'fish_variables', 'fish_history'}
    for relative in actual:
        path = Path(relative)
        if forbidden.intersection(path.parts) or relative == 'home/.config/rebos_shell/config/ai.json':
            raise ValueError('Private state found in snapshot: ' + relative)
        file = payload / relative
        if file.stat().st_size > 100 * 1024 * 1024:
            raise ValueError('File exceeds GitHub size limit: ' + relative)
        try:
            text = file.read_text()
        except UnicodeError:
            continue
        if str(home) in text:
            raise ValueError('Source home path remains in snapshot: ' + relative)
        if '-----BEGIN OPENSSH PRIVATE KEY-----' in text or '-----BEGIN RSA PRIVATE KEY-----' in text:
            raise ValueError('Private key found in snapshot: ' + relative)


def same_payload(left, right):
    if not (right / 'checksums.json').exists():
        return False
    def contents(folder):
        hashes = json.loads((folder / 'checksums.json').read_text())
        hashes.pop('manifest.json', None)  # The creation time changes on each run.
        manifest = json.loads((folder / 'manifest.json').read_text())
        manifest.pop('created', None)
        return hashes, manifest
    return contents(left) == contents(right)


def publish(repo, home, dry_run=False, push=True, builder=build):
    if git(repo, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Repository has uncommitted changes. Commit or move them before publishing.')
    branch = git(repo, 'symbolic-ref', '--short', 'HEAD')
    if not dry_run:
        git(repo, 'fetch', 'origin', branch)
        remote = git(repo, 'rev-parse', 'FETCH_HEAD')
        if git(repo, 'rev-parse', 'HEAD') != remote:
            raise ValueError('Local and GitHub branches differ. Reconcile them before publishing; no reset or force-push was attempted.')
    # Build and verify first. A conversion/copy failure leaves the old payload intact.
    with tempfile.TemporaryDirectory(prefix='rebos-publish-', dir=repo.parent) as directory:
        fresh = Path(directory) / 'payload'
        builder(home, fresh)
        validate(fresh, home)
        current = repo / 'desktop/payload'
        unchanged = same_payload(fresh, current)
        print('Snapshot verified: ' + str(len(json.loads((fresh / 'checksums.json').read_text()))) + ' files.')
        if dry_run:
            print('Dry run: ' + ('no payload changes.' if unchanged else 'payload would be refreshed, committed and published.'))
            return
        if unchanged:
            print('Desktop snapshot is already up to date.')
            return
        backup = Path(directory) / 'previous-payload'
        if current.exists():
            current.rename(backup)
        try:
            fresh.rename(current)
        except BaseException:
            if backup.exists():
                backup.rename(current)
            raise
    git(repo, 'add', '-A', '--', 'desktop/payload')
    git(repo, 'commit', '-m', 'Update desktop snapshot ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))
    if push:
        git(repo, 'push', 'origin', 'HEAD:refs/heads/' + branch)
        print('Published to ' + git(repo, 'remote', 'get-url', 'origin'))
    else:
        print('Snapshot committed locally. Publish with: git push origin ' + branch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home(), help='Desktop home to snapshot')
    parser.add_argument('--dry-run', action='store_true', help='Build and validate without changing Git or publishing')
    parser.add_argument('--no-push', action='store_true', help='Refresh and commit locally without publishing')
    args = parser.parse_args()
    try:
        publish(REPO, args.home.resolve(), args.dry_run, not args.no_push)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\nIf a commit succeeded but pushing failed, retry with git push origin HEAD.\n')


if __name__ == '__main__':
    main()
