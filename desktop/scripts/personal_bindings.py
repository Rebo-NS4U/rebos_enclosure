"""Capture local shortcut declarations before replacing configuration folders."""
import glob
import hashlib
import importlib.util
import os
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]


def reader():
    path = ROOT / 'payload/home/.config/quickshell/scripts/list_keybindings.py'
    spec = importlib.util.spec_from_file_location('rebos_binding_reader', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def niri_personal(config_dir):
    data = reader().collect(config_dir, include_disabled=True)
    if data['error']:
        raise ValueError('Cannot preserve personal shortcuts: ' + data['error'])
    directory = config_dir / 'niri'
    defaults = directory / 'keybindings-defaults.kdl'
    receipt = directory / 'keybindings-defaults.sha256'
    managed = (defaults.is_file() and receipt.is_file() and
               receipt.read_text().strip() == hashlib.sha256(defaults.read_bytes()).hexdigest())
    declarations = []
    for row in data['bindings']:
        if row['group'] != 'Desktop · Niri':
            continue
        source = Path(row['source'])
        if managed and source.resolve() == (directory / 'keybindings-defaults.kdl').resolve():
            continue
        text = source.read_text()
        declarations.append('    ' + text[row['start']:row['declarationEnd']].strip())
    return ('// Personal shortcuts preserved by the installer. Loaded after defaults.\n'
            'binds {\n' + '\n'.join(declarations) + '\n}\n')


def kitty_personal(directory):
    seen, declarations = set(), []

    def visit(path):
        path = path.resolve()
        if path in seen or not path.exists():
            return
        seen.add(path)
        pending = ''
        for line in path.read_text().splitlines(keepends=True):
            pending += line
            if line.rstrip().endswith('\\'):
                continue
            logical = pending.replace('\\\n', '')
            words = logical.split(None, 1)
            directive = words[0] if words else ''
            if directive == 'include':
                if len(words) != 2:
                    raise ValueError('Cannot preserve an empty Kitty include')
                filename = words[1].strip()
                # Kitty accepts an unquoted filename with spaces after include.
                if filename.startswith(('"', "'")):
                    try:
                        filename, = shlex.split(filename, comments=True)
                    except ValueError as error:
                        raise ValueError('Cannot preserve a Kitty include: ' + str(error)) from error
                pattern = Path(os.path.expandvars(filename)).expanduser()
                if not pattern.is_absolute():
                    pattern = path.parent / pattern
                for match in sorted(glob.glob(str(pattern))):
                    visit(Path(match))
            elif directive in {'map', 'mouse_map', 'kitty_mod', 'clear_all_shortcuts', 'action_alias'}:
                # Kitty mapping arguments are not shell commands. Keep them verbatim,
                # including quotes and option syntax that shlex cannot interpret.
                declarations.append(pending.rstrip())
            pending = ''
        if pending.strip():
            raise ValueError('Cannot preserve an unfinished Kitty shortcut declaration')

    visit(directory / 'kitty.conf')
    return '# Personal mappings preserved by the installer. Loaded after defaults.\n' + '\n'.join(declarations) + '\n'


def capture(config_dir, units):
    result = {}
    if '.config/niri' in units and (config_dir / 'niri').is_dir():
        result['.config/niri'] = ('keybindings-personal.kdl', niri_personal(config_dir))
    if '.config/kitty' in units and (config_dir / 'kitty').is_dir():
        result['.config/kitty'] = ('keybindings-personal.conf', kitty_personal(config_dir / 'kitty'))
    return result


def apply(directory, filename, content):
    personal = directory / filename
    # Destination is a freshly installed local copy, never an old source link.
    personal.write_text(content)
    personal.chmod(0o600)
    config = directory / ('config.kdl' if filename.endswith('.kdl') else 'kitty.conf')
    include = f'include "{filename}"' if filename.endswith('.kdl') else f'include {filename}'
    lines = config.read_text().splitlines()
    lines = [line for line in lines if line.strip() != include]
    config.write_text('\n'.join(lines).rstrip() + '\n\n' + include + '\n')


def record_defaults(directory):
    defaults = directory / 'keybindings-defaults.kdl'
    if defaults.is_file():
        (directory / 'keybindings-defaults.sha256').write_text(hashlib.sha256(defaults.read_bytes()).hexdigest() + '\n')
