#!/usr/bin/env python3
"""Verify, install and restore the selected user files without following existing links."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

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


def install(payload, home, dry_run=False, cbonsai=None, settings=None, preserve_preferences=False):
    units = verify(payload)
    if preserve_preferences and settings is not None:
        raise ValueError('Preference-preserving updates cannot replace the installation plan')
    if preserve_preferences:
        def preference(relative):
            if (relative == '.config/regreet-sync/regreet.css.in' or
                    relative.startswith(('.config/scripts/', '.config/systemd/user/'))):
                return False  # Managed application code, refreshed on updates.
            return ((relative.startswith(('.config/', '.cache/')) and
                     relative != '.config/quickshell') or
                    relative == 'code/rebos-assistant/config' or
                    relative.startswith('.local/share/wallpapers/'))
        # Keep existing preferences in place, including relative and broken links.
        # Moving them into the backup would change what relative links resolve to.
        units = [relative for relative in units
                 if not (preference(relative) and exists(home / relative))]
        # Fish contains personal configuration as well as this shipped command.
        # Refresh only the command when preserving an existing Fish directory.
        fish_update = '.config/fish/functions/update.fish'
        if ('.config/fish' not in units and
                (payload / 'home' / fish_update).is_file()):
            units.append(fish_update)
    # Capture shortcuts before any backup or replacement, including included files.
    spec = importlib.util.spec_from_file_location('personal_bindings', Path(__file__).with_name('personal_bindings.py'))
    personal_bindings = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(personal_bindings)
    personal = personal_bindings.capture(home / '.config', units)
    generated = {}
    if settings is not None:
        from setup import PRIME, validate_plan
        settings = validate_plan(settings)
        if '.config/niri' not in units:
            raise ValueError('Interactive settings require the bundled Niri configuration')
        generated['.local/state/rebos-desktop/installation.json'] = (json.dumps(settings, indent=2) + '\n', 0o600)
        if settings['hybrid']:
            generated['.local/bin/rebos-prime-run'] = (PRIME, 0o755)
        units += list(generated)
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
        if personal:
            print('Would retain existing Niri and Kitty shortcuts in personal files loaded after defaults')
        if settings is not None:
            print('Would write selected monitor settings and save the installation plan with the same backup/restore protection')
        return None
    backup = home / '.local/state/rebos-desktop/backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    check_parent(home, str(backup.relative_to(home)) + '/journal.json')
    backup.mkdir(parents=True)
    print(f'Desktop recovery backup: {backup}', flush=True)
    journal = {'home': str(home), 'entries': []}
    def save_journal():
        (backup / 'journal.json').write_text(json.dumps(journal, indent=2))

    save_journal()

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
        if relative in generated:
            content, mode = generated[relative]
            destination.write_text(content)
            destination.chmod(mode)
        elif source.is_dir():
            shutil.copytree(source, destination)
            for path in destination.rglob('*'):
                if path.is_file():
                    expand(path, home)
            if relative == '.config/niri' and settings is not None:
                from setup import customize_niri
                customize_niri(destination, settings)
            if relative == '.config/niri':
                personal_bindings.record_defaults(destination)
            if relative in personal:
                personal_bindings.apply(destination, *personal[relative])
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
    parser.add_argument('--setup-stdin', action='store_true')
    args = parser.parse_args()
    try:
        if args.restore:
            restore(args.restore.resolve())
        elif args.verify:
            print(f'Payload checksums OK: {len(verify(args.payload))} install entries')
        else:
            settings = json.load(sys.stdin) if args.setup_stdin else None
            install(args.payload, args.home.absolute(), args.dry_run, args.cbonsai, settings)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Deployment error: {error}\n')
