#!/usr/bin/env python3
"""Verify, install and restore the selected user files without following existing links."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def exists(path):
    return path.exists() or path.is_symlink()


def check_parent(home, relative, allow_config_links=False):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError(f'Unsafe relative path: {relative}')
    current = home
    for part in path.parts[:-1]:
        current = current / part
        if current.is_symlink() and allow_config_links:
            parts = current.relative_to(home).parts
            if len(parts) >= 2 and parts[0] == '.config' and current.is_dir():
                continue
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            raise ValueError(f'Parent must be a real directory: {current}')


def verify(payload):
    hashes = json.loads((payload / 'checksums.json').read_text())
    actual = {str(p.relative_to(payload)) for p in payload.rglob('*') if p.is_file()}
    if actual != set(hashes) | {'checksums.json'}:
        raise ValueError('Payload file inventory has changed; rebuild its snapshot')
    for relative, expected in hashes.items():
        path = payload / relative
        check_parent(payload, relative)
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Payload checksum mismatch: {relative}')
    return json.loads((payload / 'manifest.json').read_text())['units']


def expand(path, home):
    # Binary files are unchanged. Configs may contain portable home placeholders.
    try:
        content = path.read_text()
    except UnicodeError:
        return
    if '@HOME@' in content:
        path.write_text(content.replace('@HOME@', str(home)))


def install(payload, home, dry_run=False, cbonsai=None):
    units = verify(payload)
    # Preflight all destination parents before touching any of them.
    for relative in units:
        check_parent(home, relative, allow_config_links=True)
    linked_parents = sorted({str(parent.relative_to(home)) for relative in units
                             for parent in (home / relative).parents
                             if home in parent.parents and parent.is_symlink()})
    if dry_run:
        print(f'Verified payload; would deploy {len(units)} entries into {home}')
        for parent in linked_parents:
            print(f'Would back up linked folder {home / parent} and install into a local copy; its source stays unchanged')
        return None
    backup = home / '.local/state/rebos-desktop/backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    check_parent(home, str(backup.relative_to(home)) + '/journal.json')
    backup.mkdir(parents=True)
    journal = {'home': str(home), 'entries': []}
    def save_journal():
        (backup / 'journal.json').write_text(json.dumps(journal, indent=2))

    def detach_parents(relative):
        current = home
        for part in Path(relative).parts[:-1]:
            current = current / part
            if not current.is_symlink():
                continue
            origin = current.resolve(strict=True)
            # Separate storage prevents a later leaf backup writing through a saved parent link.
            saved_relative = f'parent-links/{len(journal["entries"])}'
            saved = backup / saved_relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            journal['entries'].append({'path': str(current.relative_to(home)),
                                       'existed': True, 'saved': saved_relative})
            save_journal()
            current.rename(saved)
            shutil.copytree(origin, current, symlinks=True)

    for relative in units:
        detach_parents(relative)
        source, destination, saved = payload / 'home' / relative, home / relative, backup / 'files' / relative
        entry = {'path': relative, 'existed': exists(destination)}
        # Journal before each mutation so interrupted deployments remain recoverable.
        journal['entries'].append(entry)
        (backup / 'journal.json').write_text(json.dumps(journal, indent=2))
        destination.parent.mkdir(parents=True, exist_ok=True)
        if entry['existed']:
            saved.parent.mkdir(parents=True, exist_ok=True)
            destination.rename(saved)
        if source.is_dir():
            shutil.copytree(source, destination)
            for path in destination.rglob('*'):
                if path.is_file():
                    expand(path, home)
        else:
            shutil.copy2(source, destination)
            expand(destination, home)
    if cbonsai:
        destination = home / '.local/bin/cbonsai'
        relative = str(destination.relative_to(home))
        entry = {'path': relative, 'existed': exists(destination)}
        journal['entries'].append(entry)
        (backup / 'journal.json').write_text(json.dumps(journal, indent=2))
        if entry['existed']:
            saved = backup / 'files' / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            destination.rename(saved)
        shutil.copy2(cbonsai, destination)
    print(f'Installed desktop files. Backup: {backup}')
    return backup


def restore(backup):
    journal = json.loads((backup / 'journal.json').read_text())
    home = Path(journal['home'])
    for entry in reversed(journal['entries']):
        relative = entry['path']
        check_parent(home, relative)
        destination = home / relative
        saved = backup / entry.get('saved', 'files/' + relative)
        # A journal entry with no saved original may have been interrupted before the move.
        if entry['existed'] and not exists(saved):
            continue
        if exists(destination):
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        if entry['existed']:
            destination.parent.mkdir(parents=True, exist_ok=True)
            saved.rename(destination)
    (backup / 'journal.json').rename(backup / 'restored-journal.json')
    print(f'Restored files from {backup}; packages and system services are unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--payload', type=Path, default=ROOT / 'payload')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--cbonsai', type=Path)
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    try:
        if args.restore:
            restore(args.restore.resolve())
        elif args.verify:
            print(f'Payload checksums OK: {len(verify(args.payload))} install entries')
        else:
            install(args.payload, args.home.absolute(), args.dry_run, args.cbonsai)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Deployment error: {error}\n')
