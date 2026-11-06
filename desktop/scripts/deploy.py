#!/usr/bin/env python3
"""Verify, install and restore the selected user files without following existing links."""
import argparse
from datetime import datetime, timezone
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import (source as source_path, destination_name, checksum_path,
                    inventory, manifest, entry as source_entry, checkout_for, safe)

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
    if manifest(payload).get('layout') == 2:
        actual = inventory(payload)
        if set(actual) != set(hashes):
            raise ValueError('Payload file inventory has changed; rebuild its snapshot')
        for name, path in actual.items():
            root = payload if name == 'manifest.json' else payload.parents[1]
            check_parent(root, str(path.relative_to(root)))
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != hashes[name]:
                raise ValueError('Payload checksum mismatch: ' + name)
        sources = manifest(payload)['sources']
        units = manifest(payload)['units']
        if set(sources) != set(units):
            raise ValueError('Each installation unit needs one source mapping')
        for name in units:
            safe(name)
            item = sources[name]
            if item.get('kind') not in ('managed', 'personal', 'cache') or not source_path(payload, name).exists():
                raise ValueError('Invalid source mapping: ' + name)
            expected = 'config' if item['kind'] == 'personal' else 'system'
            if Path(item['source']).parts[0] != expected:
                raise ValueError('Source kind does not match its configuration/system directory: ' + name)
        return units
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


def organized_destination(home, relative):
    path = home / relative
    resolved = path.resolve()
    if resolved.is_relative_to(home / '.config/enclosure'):
        return resolved
    return path


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
        scopes = [str(payload)]
        if manifest(payload).get('layout') == 2:
            scopes += [str(checkout / 'config'), str(checkout / 'system')]
        return {'repository': 'https://github.com/Rebo-NS4U/rebos_enclosure',
                'commit': git('rev-parse', 'HEAD'),
                'dirty': bool(git('status', '--porcelain', '--', *scopes))}
    except (OSError, subprocess.SubprocessError):
        return None


RETIRED_BONSAI_PATHS = (
    '.local/bin/terminal-bonsai', '.local/bin/cbonsai', '.local/bin/terminal-rainforest',
    '.local/share/cbonsai', '.local/share/terminal-rainforest',
    '.local/share/enclosure/system/bin/terminal-bonsai',
    '.local/share/enclosure/system/bin/cbonsai',
    '.local/share/enclosure/system/bin/terminal-rainforest',
    '.local/share/enclosure/system/share/cbonsai',
    '.local/share/enclosure/system/share/terminal-rainforest',
)


def retire_bonsai_alternatives(home, backup=None, journal=None, dry_run=False):
    """Archive retired commands and assets without following their symlinks."""
    paths = [name for name in RETIRED_BONSAI_PATHS if exists(home / name)]
    # Validate every parent before moving anything; never traverse external links.
    for name in paths:
        check_parent(home, name)
    for name in paths:
        if dry_run:
            print(f'Would archive retired bonsai files: {home / name}')
            continue
        destination = backup / 'files' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        journal['entries'].append({'path': name, 'existed': True})
        (backup / 'journal.json').write_text(json.dumps(journal, indent=2))
        (home / name).rename(destination)
    return paths


def is_preference(payload, relative):
    if manifest(payload).get('layout') == 2:
        return source_entry(payload, relative)[1]['kind'] in ('personal', 'cache')
    if (relative == '.config/regreet-sync/regreet.css.in' or
            relative.startswith(('.config/scripts/', '.config/systemd/user/'))):
        return False  # Managed application code, refreshed on updates.
    return ((relative.startswith(('.config/', '.cache/')) and
             relative != '.config/quickshell') or
            relative == 'code/rebos-assistant/config' or
            relative.startswith('.local/share/wallpapers/'))


def recorded_default_digest(payload, home, path, revision):
    """Recover a shipped default from a recorded revision, never personal state."""
    name = destination_name(payload, path)
    candidates = [f'desktop/payload/home/{name}']
    if manifest(payload).get('layout') == 2:
        candidates.insert(0, str(path.relative_to(payload.parents[1])))
    for candidate in candidates:
        try:
            old = subprocess.check_output(
                ['git', '-C', str(ROOT.parent), 'show', f'{revision}:{candidate}'],
                stderr=subprocess.PIPE, timeout=10)
            old = old.replace(b'@HOME@', str(home).encode())
            return hashlib.sha256(old).hexdigest()
        except (OSError, subprocess.SubprocessError):
            pass
    return None


def preference_file_update(payload, home, path, previous, installed_commit):
    """Return a default fingerprint and whether its installed copy may change."""
    name = destination_name(payload, path)
    content = path.read_bytes().replace(b'@HOME@', str(home).encode())
    digest = hashlib.sha256(content).hexdigest()
    destination = home / name
    # Preserve links (including linked parents) and unknown existing
    # preferences. The first update establishes a safe baseline.
    parents = destination.relative_to(home).parents
    links = [destination, *(home / p for p in parents)]
    if any(p.is_symlink() and not p.resolve().is_relative_to(home / '.config/enclosure') for p in links):
        return name, digest, False
    if not exists(destination):
        # A missing previously shipped file may be an intentional
        # personal deletion. Only add genuinely new defaults.
        if name not in previous:
            return name, digest, True
    elif destination.is_file():
        current = hashlib.sha256(destination.read_bytes()).hexdigest()
        # Older installations have a revision but no defaults record.
        # Recover the old shipped default when its Git object exists.
        if name not in previous and installed_commit:
            recovered = recorded_default_digest(payload, home, path, installed_commit)
            if recovered is not None:
                previous[name] = recovered
        if current == previous.get(name) and current != digest:
            return name, digest, True
        elif current != digest:
            print(f'Keeping personal configuration: {name}')
    return name, digest, False


def load_preference_baseline(home):
    """Load recorded default hashes and a usable installed Git revision."""
    record = home / '.local/state/rebos-desktop/preference-defaults.json'
    previous = json.loads(record.read_text()) if record.is_file() else {}
    installed_record = home / '.local/state/rebos-desktop/source.json'
    installed_commit = (json.loads(installed_record.read_text()).get('commit', '')
                        if installed_record.is_file() else '')
    if len(installed_commit) != 40 or any(c not in '0123456789abcdef' for c in installed_commit):
        installed_commit = ''
    return previous, installed_commit


def select_preference_updates(payload, home, units):
    """Plan updates to shipped defaults while retaining personal changes."""
    # Track shipped defaults, never personal contents. Update individual
    # unchanged files instead of skipping an entire configuration directory.
    previous, installed_commit = load_preference_baseline(home)
    defaults = {}
    selected = []
    for relative in units:
        if not is_preference(payload, relative):
            selected.append(relative)
            continue
        source = source_path(payload, relative)
        # Generated palettes and wallpaper choices remain personal state.
        if relative.startswith(('.cache/', '.local/share/wallpapers/')):
            if not exists(home / relative):
                selected.append(relative)
            continue
        paths = sorted(source.rglob('*')) if source.is_dir() else [source]
        for path in paths:
            if not path.is_file():
                continue
            name, digest, replace = preference_file_update(payload, home, path, previous, installed_commit)
            defaults[name] = digest
            if replace:
                selected.append(name)
    units = selected
    # Fish contains personal configuration as well as this shipped command.
    # Refresh only the command when preserving an existing Fish directory.
    fish_update = '.config/fish/functions/update.fish'
    if (manifest(payload).get('layout') != 2 and '.config/fish' not in units and fish_update not in units and
            source_path(payload, fish_update).is_file()):
        units.append(fish_update)
    return units, defaults


def plan_source_links(payload, home, units, link_source):
    """Validate source ownership and choose links before deployment mutates files."""
    linked = {}
    if link_source:
        payload = payload.resolve()
        checkout = payload.parent.parent
        if payload.name != 'payload' or payload.parent.name != 'desktop' or not (checkout / '.git').exists():
            raise ValueError('--link-source requires a persistent Git checkout')
        for root in SOURCE_ROOTS:
            selected = [unit for unit in units if unit == root or unit.startswith(root + '/')]
            if selected:
                linked[root] = source_path(payload, root)
                units = [unit for unit in units if unit not in selected] + [root]
        # Portable commands and service definitions can use the same file too.
        # Home-expanded templates and personal configuration remain local files.
        for relative in units:
            source = source_path(payload, relative)
            if (relative.startswith(('.local/bin/', '.config/scripts/',
                                     '.config/systemd/user/', '.local/share/applications/'))
                    and source.is_file() and b'@HOME@' not in source.read_bytes()):
                linked[relative] = source
    else:
        for root in SOURCE_ROOTS:
            target = home / root
            if target.is_symlink() and checkout_for(target) is not None:
                raise ValueError('Checkout-managed sources require --link-source; refusing to recreate duplicate code')
    return payload, units, linked


@dataclass
class DeploymentOptions:
    dry_run: bool = False
    settings: dict | None = None
    preserve_preferences: bool = False
    link_source: bool = False


@dataclass
# Quality exception: A typed deployment schema names the journaled inputs explicitly; it is not a behavior-heavy object.
# Numeric ceilings are enforced by desktop/scripts/quality.py.
class InstallPlan:  # pylint: disable=too-many-instance-attributes
    payload: Path
    home: Path
    units: list
    linked: dict
    generated: dict
    personal: dict
    personal_bindings: object
    settings: dict | None
    provenance: dict | None
    linked_parents: list


def load_binding_module():
    spec = importlib.util.spec_from_file_location('personal_bindings', Path(__file__).with_name('personal_bindings.py'))
    personal_bindings = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(personal_bindings)
    return personal_bindings


# Quality exception: Explicit paths, fingerprints and recovery records preserve auditability at the file-mutation boundary.
# Numeric ceilings are enforced by desktop/scripts/quality.py.
def prepare_install(payload, home, options):  # pylint: disable=too-many-locals
    settings = options.settings
    preserve_preferences, link_source = options.preserve_preferences, options.link_source
    units = verify(payload)
    if manifest(payload).get('layout') == 2:
        from organize import plan as organization_plan
        organization_plan(home, payload)  # Detect conflicting locations before any writes.
    if preserve_preferences and settings is not None:
        raise ValueError('Preference-preserving updates cannot replace the installation plan')
    defaults = {}
    if preserve_preferences:
        units, defaults = select_preference_updates(payload, home, units)
    payload, units, linked = plan_source_links(payload, home, units, link_source)
    # Capture shortcuts before any backup or replacement, including included files.
    personal_bindings = load_binding_module()
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
    return InstallPlan(payload, home, units, linked, generated, personal, personal_bindings, settings, provenance, linked_parents)


def preview_install(plan):
    from organize import plan as organization_plan
    if '.local/bin/bonsai-grow' in plan.units:
        retire_bonsai_alternatives(plan.home, dry_run=True)
    print(f'Verified payload; would deploy {len(plan.units)} entries into {plan.home}')
    if manifest(plan.payload).get('layout') == 2:
        print(f'Personal settings: {plan.home / ".config/enclosure"}')
        print(f'Managed files: {plan.home / ".local/share/enclosure/system"}; development source links are retained')
        print(f'Shipped defaults: {plan.home / ".local/share/enclosure/defaults"}')
        for old, new in organization_plan(plan.home, plan.payload):
            print(f'Would group {old} -> {new}')
    for parent in plan.linked_parents:
        print(f'Would back up linked folder {plan.home / parent} and install into a local copy; its source stays unchanged')
    for relative, source in plan.linked.items():
        print(f'Would link {plan.home / relative} to {source}')
    if plan.personal:
        print('Would retain existing Niri and Kitty shortcuts in personal files loaded after defaults')
    if plan.settings is not None:
        print('Would write selected monitor settings and save the installation plan with the same backup/restore protection')
    return None


class DeploymentWriter:
    """Apply one preflighted plan, journaling each mutation before it happens."""
    def __init__(self, plan):
        backup = plan.home / '.local/state/rebos-desktop/backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        check_parent(plan.home, str(backup.relative_to(plan.home)) + '/journal.json')
        backup.mkdir(parents=True, mode=0o700)
        print(f'Desktop recovery backup: {backup}', flush=True)
        journal = {'home': str(plan.home), 'entries': []}
        self.plan = plan
        self.backup, self.journal = backup, journal
        self.save_journal()

    def save_journal(self):
        (self.backup / 'journal.json').write_text(json.dumps(self.journal, indent=2))

    def detach_parents(self, relative):
        current = self.plan.home
        for part in Path(relative).parts[:-1]:
            current = current / part
            if not current.is_symlink():
                continue
            if current.resolve().is_relative_to(self.plan.home / '.config/enclosure'):
                continue
            origin = current.resolve(strict=True)
            # Separate storage prevents a later leaf backup writing through a saved parent link.
            saved_relative = f'parent-links/{len(self.journal["entries"])}'
            saved = self.backup / saved_relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            self.journal['entries'].append({'path': str(current.relative_to(self.plan.home)),
                                       'existed': True, 'saved': saved_relative})
            self.save_journal()
            current.rename(saved)
            shutil.copytree(origin, current, symlinks=True)


    def install_unit(self, relative):
        self.detach_parents(relative)
        source = source_path(self.plan.payload, relative)
        destination = organized_destination(self.plan.home, relative)
        destination_relative = str(destination.relative_to(self.plan.home))
        check_parent(self.plan.home, destination_relative)
        saved = self.backup / 'files' / destination_relative
        entry = {'path': destination_relative, 'existed': exists(destination)}
        self.journal['entries'].append(entry)
        (self.backup / 'journal.json').write_text(json.dumps(self.journal, indent=2))
        destination.parent.mkdir(parents=True, exist_ok=True)
        if entry['existed']:
            saved.parent.mkdir(parents=True, exist_ok=True)
            destination.rename(saved)
        self.write_source(relative, source, destination)

    def write_source(self, relative, source, destination):
        if relative in self.plan.linked:
            destination.symlink_to(self.plan.linked[relative], target_is_directory=self.plan.linked[relative].is_dir())
        elif relative in self.plan.generated:
            content, mode = self.plan.generated[relative]
            destination.write_text(content)
            destination.chmod(mode)
        elif source.is_dir():
            shutil.copytree(source, destination)
            for path in destination.rglob('*'):
                if path.is_file():
                    expand(path, self.plan.home)
            if relative == '.config/niri' and self.plan.settings is not None:
                from setup import customize_niri
                customize_niri(destination, self.plan.settings)
            if relative == '.config/niri':
                self.plan.personal_bindings.record_defaults(destination)
            if relative in self.plan.personal:
                self.plan.personal_bindings.apply(destination, *self.plan.personal[relative])
        else:
            shutil.copy2(source, destination)
            expand(destination, self.plan.home)

    def record_provenance(self):
        fingerprints = {}
        for relative in self.plan.units:
            if not (relative.startswith(('.local/bin/', '.config/scripts/', '.config/quickshell/', 'code/anime-streamer/')) or relative == '.config/quickshell' or (relative.startswith('code/rebos-assistant/') and (not relative.startswith('code/rebos-assistant/config')))):
                continue
            source = source_path(self.plan.payload, relative)
            sources = source.rglob('*') if source.is_dir() else [source]
            for path in sources:
                if path.is_file():
                    name = destination_name(self.plan.payload, path)
                    fingerprints[name] = hashlib.sha256((self.plan.home / name).read_bytes()).hexdigest()
        self.plan.provenance['files'] = fingerprints
        (self.plan.home / '.local/state/rebos-desktop/source.json').write_text(json.dumps(self.plan.provenance, indent=2) + '\n')

    def run(self):
        try:
            if '.local/bin/bonsai-grow' in self.plan.units:
                retire_bonsai_alternatives(self.plan.home, self.backup, self.journal)
            for relative in self.plan.units:
                self.install_unit(relative)
            if manifest(self.plan.payload).get('layout') == 2:
                from organize import organize
                organize(self.plan.home, self.plan.payload, self.backup, self.journal)
            if self.plan.provenance is not None:
                self.record_provenance()
        except BaseException:
            restore(self.backup)
            raise
        return self.backup


def install(payload, home, **controls):
    """Deploy with named controls; reject unknown options before changing files."""
    options = DeploymentOptions(**controls)
    plan = prepare_install(payload, home, options)
    if options.dry_run:
        return preview_install(plan)
    return DeploymentWriter(plan).run()


def restore(backup):
    journal = json.loads((backup / 'journal.json').read_text())
    home = Path(journal['home'])
    for entry in reversed(journal['entries']):
        relative = entry['path']
        check_parent(home, relative)
        destination = home / relative
        saved = backup / entry.get('saved', 'files/' + relative)
        if 'moved_to' in entry:
            moved = home / entry['moved_to']
            check_parent(home, entry['moved_to'])
            if not exists(moved) or (exists(destination) and not destination.is_symlink()):
                continue
            if destination.is_symlink():
                destination.unlink()
            moved.rename(destination)
            if 'original_link' in entry:
                destination.unlink()
                destination.symlink_to(entry['original_link'])
            for name, target in entry.get('external_links', {}).items():
                link = destination / name
                link.unlink()
                link.symlink_to(target)
            continue
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
            install(args.payload, args.home.absolute(), dry_run=args.dry_run, settings=settings,
                    preserve_preferences=args.preserve_preferences, link_source=args.link_source)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Deployment error: {error}\n')
