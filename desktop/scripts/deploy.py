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
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ('.config/quickshell', 'code/rebos-assistant', 'code/anime-streamer')


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
    actual = {str(p.relative_to(payload)) for p in payload.rglob('*')
              if p.is_file() and p.name not in {'checksums.json', 'manifest.json'}
              and '__pycache__' not in p.relative_to(payload).parts}
    if actual != set(hashes) - {'manifest.json'}:
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


def source_record(payload):
    """Identify the actual payload checkout, never an unrelated parent repository."""
    payload = payload.resolve()
    def git(*args):
        return subprocess.check_output(['git', '-C', str(payload), *args],
                                       text=True, stderr=subprocess.PIPE, timeout=20).strip()
    try:
        checkout = Path(git('rev-parse', '--show-toplevel'))
        if checkout / 'desktop/payload' != payload:
            return None
        origin = git('remote', 'get-url', 'origin')
        if origin.removesuffix('.git').rstrip('/') not in (
                'https://github.com/Rebo-NS4U/rebos_enclosure',
                'git@github.com:Rebo-NS4U/rebos_enclosure'):
            return None
        return {'repository': 'https://github.com/Rebo-NS4U/rebos_enclosure',
                'commit': git('rev-parse', 'HEAD'),
                'dirty': bool(git('status', '--porcelain', '--', str(payload)))}
    except (OSError, subprocess.SubprocessError):
        return None


def install(payload, home, dry_run=False, cbonsai=None, settings=None, preserve_preferences=False,
            link_source=False):
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
        # Track shipped defaults, never personal contents. Update individual
        # unchanged files instead of skipping an entire configuration directory.
        record = home / '.local/state/rebos-desktop/preference-defaults.json'
        previous = json.loads(record.read_text()) if record.is_file() else {}
        installed_record = home / '.local/state/rebos-desktop/source.json'
        installed_commit = (json.loads(installed_record.read_text()).get('commit', '')
                            if installed_record.is_file() else '')
        if len(installed_commit) != 40 or any(c not in '0123456789abcdef' for c in installed_commit):
            installed_commit = ''
        defaults = {}
        selected = []
        for relative in units:
            if not preference(relative):
                selected.append(relative)
                continue
            source = payload / 'home' / relative
            # Generated palettes and wallpaper choices remain personal state.
            if relative.startswith(('.cache/', '.local/share/wallpapers/')):
                if not exists(home / relative):
                    selected.append(relative)
                continue
            paths = sorted(source.rglob('*')) if source.is_dir() else [source]
            for path in paths:
                if not path.is_file():
                    continue
                name = str(path.relative_to(payload / 'home'))
                content = path.read_bytes().replace(b'@HOME@', str(home).encode())
                digest = hashlib.sha256(content).hexdigest()
                defaults[name] = digest
                destination = home / name
                # Preserve links (including linked parents) and unknown existing
                # preferences. The first update establishes a safe baseline.
                parents = destination.relative_to(home).parents
                if destination.is_symlink() or any((home / p).is_symlink() for p in parents):
                    continue
                if not exists(destination):
                    # A missing previously shipped file may be an intentional
                    # personal deletion. Only add genuinely new defaults.
                    if name not in previous:
                        selected.append(name)
                elif destination.is_file():
                    current = hashlib.sha256(destination.read_bytes()).hexdigest()
                    # Older installations have a revision but no defaults record.
                    # Recover the old shipped default when its Git object exists.
                    if name not in previous and installed_commit:
                        try:
                            old = subprocess.check_output(
                                ['git', '-C', str(ROOT.parent), 'show',
                                 f'{installed_commit}:desktop/payload/home/{name}'],
                                stderr=subprocess.PIPE, timeout=10)
                            old = old.replace(b'@HOME@', str(home).encode())
                            previous[name] = hashlib.sha256(old).hexdigest()
                        except (OSError, subprocess.SubprocessError):
                            pass
                    if current == previous.get(name) and current != digest:
                        selected.append(name)
                    elif current != digest:
                        print(f'Keeping personal configuration: {name}')
        units = selected
        # Fish contains personal configuration as well as this shipped command.
        # Refresh only the command when preserving an existing Fish directory.
        fish_update = '.config/fish/functions/update.fish'
        if ('.config/fish' not in units and fish_update not in units and
                (payload / 'home' / fish_update).is_file()):
            units.append(fish_update)
    linked = {}
    if link_source:
        payload = payload.resolve()
        checkout = payload.parent.parent
        if payload.name != 'payload' or payload.parent.name != 'desktop' or not (checkout / '.git').exists():
            raise ValueError('--link-source requires a persistent Git checkout')
        for root in SOURCE_ROOTS:
            selected = [unit for unit in units if unit == root or unit.startswith(root + '/')]
            if selected:
                linked[root] = payload / 'home' / root
                units = [unit for unit in units if unit not in selected] + [root]
        # Portable commands and service definitions can use the same file too.
        # Home-expanded templates and personal configuration remain local files.
        for relative in units:
            source = payload / 'home' / relative
            if (relative.startswith(('.local/bin/', '.config/scripts/',
                                     '.config/systemd/user/', '.local/share/applications/'))
                    and source.is_file() and b'@HOME@' not in source.read_bytes()):
                linked[relative] = source
    else:
        for root in SOURCE_ROOTS:
            target = home / root
            if target.is_symlink() and 'desktop/payload/home' in str(target.resolve()):
                raise ValueError('Checkout-managed sources require --link-source; refusing to recreate duplicate code')
    # Capture shortcuts before any backup or replacement, including included files.
    spec = importlib.util.spec_from_file_location('personal_bindings', Path(__file__).with_name('personal_bindings.py'))
    personal_bindings = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(personal_bindings)
    personal = personal_bindings.capture(home / '.config', units)
    generated = {}
    if preserve_preferences:
        relative = '.local/state/rebos-desktop/preference-defaults.json'
        generated[relative] = (json.dumps(defaults, indent=2) + '\n', 0o600)
        units.append(relative)
    provenance = source_record(payload)
    if provenance is not None:
        relative = '.local/state/rebos-desktop/source.json'
        generated[relative] = (json.dumps(provenance, indent=2) + '\n', 0o600)
        units.append(relative)
    if settings is not None:
        from setup import PRIME, validate_plan
        settings = validate_plan(settings)
        if '.config/niri' not in units:
            raise ValueError('Interactive settings require the bundled Niri configuration')
        generated['.local/state/rebos-desktop/installation.json'] = (json.dumps(settings, indent=2) + '\n', 0o600)
        if settings['hybrid']:
            generated['.local/bin/rebos-prime-run'] = (PRIME, 0o755)
        units += [relative for relative in generated if relative not in units]
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
        for relative, source in linked.items():
            print(f'Would link {home / relative} to {source}')
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

    try:
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
            if relative in linked:
                destination.symlink_to(linked[relative], target_is_directory=linked[relative].is_dir())
            elif relative in generated:
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
        if provenance is not None:
            # Fingerprint deployed managed code, excluding preserved preferences,
            # account directories, caches and files not supplied by the payload.
            fingerprints = {}
            for relative in units:
                if not (relative.startswith(('.local/bin/', '.config/scripts/', '.config/quickshell/',
                                             'code/anime-streamer/')) or
                        relative == '.config/quickshell' or
                        (relative.startswith('code/rebos-assistant/') and
                         not relative.startswith('code/rebos-assistant/config'))):
                    continue
                source = payload / 'home' / relative
                sources = source.rglob('*') if source.is_dir() else [source]
                for path in sources:
                    if path.is_file():
                        name = str(path.relative_to(payload / 'home'))
                        fingerprints[name] = hashlib.sha256((home / name).read_bytes()).hexdigest()
            provenance['files'] = fingerprints
            (home / '.local/state/rebos-desktop/source.json').write_text(json.dumps(provenance, indent=2) + '\n')
    except BaseException:
        # The journal is written before each replacement, so even partial copies
        # can be removed and their original files restored automatically.
        restore(backup)
        raise
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
    parser.add_argument('--link-source', action='store_true',
                        help='Link application sources to this persistent checkout instead of copying them')
    parser.add_argument('--preserve-preferences', action='store_true')
    args = parser.parse_args()
    try:
        if args.restore:
            restore(args.restore.resolve())
        elif args.verify:
            print(f'Payload checksums OK: {len(verify(args.payload))} install entries')
        else:
            settings = json.load(sys.stdin) if args.setup_stdin else None
            install(args.payload, args.home.absolute(), args.dry_run, args.cbonsai, settings,
                    preserve_preferences=args.preserve_preferences, link_source=args.link_source)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Deployment error: {error}\n')
