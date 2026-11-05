#!/usr/bin/env python3
"""Group installed personal settings and managed files without changing their contents."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil

from layout import manifest, checkout_for


def plan(home, payload):
    data = manifest(payload)
    if data.get('layout') != 2:
        return []
    moves = {}
    for relative, item in data['sources'].items():
        old = home / relative
        name = Path(item['source'])
        if item['kind'] == 'personal':
            component = Path(relative).parts[1]
            if component == 'enclosure':
                continue  # These settings already live in the grouped directory.
            old = home / '.config' / component
            label = 'shell' if component == 'rebos_shell' else component
            new = home / '.config/enclosure' / label
        elif item['kind'] == 'managed':
            new = home / '.local/share/enclosure/system' / name.relative_to('system')
            if old.is_symlink() and checkout_for(old) is not None:
                continue  # Development links already point to the single system source.
        else:
            continue  # Runtime cache seeds are not configuration or source.
        if not old.exists() and not old.is_symlink():
            continue
        if old.is_symlink() and old.resolve() == new.resolve():
            continue
        if item['kind'] == 'personal' and (new.exists() or new.is_symlink()):
            raise ValueError(f'Both personal configuration locations exist: {old} and {new}; reconcile them first.')
        moves[str(old.relative_to(home))] = (old, new)
    for name in ('rebos-prime-run',):
        old = home / '.local/bin' / name
        new = home / '.local/share/enclosure/system/bin' / name
        if old.exists() and not (old.is_symlink() and old.resolve() == new.resolve()):
            moves[str(old.relative_to(home))] = (old, new)
    return list(moves.values())


def defaults_match(home, payload):
    source = payload.parents[1] / 'config'
    target = home / '.local/share/enclosure/defaults'
    names = {p.relative_to(source) for p in source.rglob('*') if p.is_file()}
    actual = {p.relative_to(target) for p in target.rglob('*') if p.is_file()}
    return (names == actual and target.is_dir() and not target.is_symlink() and
            all(not (target / name).is_symlink() and (source / name).read_bytes() == (target / name).read_bytes()
                for name in names))


def organize(home, payload, backup, journal):
    from deploy import check_parent, exists
    moves = plan(home, payload)
    for old, new in moves:
        check_parent(home, str(old.relative_to(home)))
        check_parent(home, str(new.relative_to(home)))
    def save():
        (backup / 'journal.json').write_text(json.dumps(journal, indent=2))
    for old, new in moves:
        old_name, new_name = str(old.relative_to(home)), str(new.relative_to(home))
        # Keep an overwritten managed version in the same recovery journal.
        central_entry = {'path': new_name, 'existed': exists(new)}
        journal['entries'].append(central_entry)
        save()
        if central_entry['existed']:
            saved = backup / 'files' / new_name
            saved.parent.mkdir(parents=True, exist_ok=True)
            new.rename(saved)
        move_entry = {'path': old_name, 'existed': True, 'moved_to': new_name}
        if old.is_symlink():
            move_entry['original_link'] = os.readlink(old)
        external_links = {}
        if old.is_dir() and not old.is_symlink():
            for path in old.rglob('*'):
                if path.is_symlink() and not Path(os.readlink(path)).is_absolute() and not path.resolve().is_relative_to(old.resolve()):
                    name = str(path.relative_to(old))
                    external_links[name] = (os.readlink(path), path.resolve())
            if external_links:
                move_entry['external_links'] = {name: target for name, (target, _) in external_links.items()}
        journal['entries'].append(move_entry)
        save()
        new.parent.mkdir(parents=True, exist_ok=True)
        # Preserve relative external links when relocating their directory entry.
        target = old.resolve() if old.is_symlink() else None
        old.rename(new)
        if target is not None:
            new.unlink()
            new.symlink_to(target, target_is_directory=target.is_dir())
        for name, (_, target) in external_links.items():
            path = new / name
            path.unlink()
            path.symlink_to(target, target_is_directory=target.is_dir())
        old.symlink_to(new, target_is_directory=new.is_dir())
        print(f'Grouped {old_name} -> {new_name}')
    if not defaults_match(home, payload):
        target = home / '.local/share/enclosure/defaults'
        name = str(target.relative_to(home))
        check_parent(home, name)
        existed = exists(target)
        journal['entries'].append({'path': name, 'existed': existed})
        save()
        if existed:
            saved = backup / 'files' / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            target.rename(saved)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(payload.parents[1] / 'config', target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--payload', type=Path, default=Path(__file__).resolve().parents[1] / 'payload')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    args.home = args.home.expanduser().absolute()
    args.payload = args.payload.expanduser().absolute()
    from deploy import verify, restore
    verify(args.payload)
    moves = plan(args.home, args.payload)
    if not args.apply:
        for old, new in moves:
            print(f'Would group {old} -> {new}')
        if not defaults_match(args.home, args.payload):
            print('Would refresh managed defaults in ~/.local/share/enclosure/defaults')
        return
    if not moves and defaults_match(args.home, args.payload):
        print('Installed files are already grouped.')
        return
    backup = args.home / '.local/state/rebos-desktop/backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup.mkdir(parents=True, mode=0o700)
    journal = {'home': str(args.home), 'entries': []}
    try:
        organize(args.home, args.payload, backup, journal)
    except BaseException:
        if (backup / 'journal.json').exists():
            restore(backup)
        raise
    print('Organization complete; recovery backup: ' + str(backup))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
