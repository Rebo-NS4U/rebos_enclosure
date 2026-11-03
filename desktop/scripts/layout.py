"""Resolve shipped defaults and managed source without depending on installed paths."""
import json
from pathlib import Path


def manifest(payload):
    if not (payload / 'manifest.json').exists():
        return {}  # Old health-check fixtures and legacy release layouts.
    return json.loads((payload / 'manifest.json').read_text())


def safe(relative):
    path = Path(relative)
    if path.is_absolute() or not path.parts or '..' in path.parts:
        raise ValueError('Unsafe source path: ' + str(relative))
    return path


def entry(payload, relative):
    safe(relative)
    sources = manifest(payload).get('sources', {})
    for name in sorted(sources, key=len, reverse=True):
        if relative == name or relative.startswith(name + '/'):
            item = sources[name]
            return name, item, Path(relative).relative_to(name)
    if sources:
        return None
    return relative, {'source': 'home/' + relative, 'kind': 'legacy'}, Path('.')


def source(payload, relative):
    item = entry(payload, relative)
    if item is None:
        # Generated installation records and optional helpers have no source.
        return payload / 'generated' / safe(relative)
    _, data, tail = item
    name = safe(data['source'])
    if manifest(payload).get('layout') == 2:
        if name.parts[0] not in ('config', 'system'):
            raise ValueError('Source must be under config/ or system/')
        return payload.parents[1] / name / tail
    return payload / name / tail


def destination_name(payload, path):
    data = manifest(payload)
    if data.get('layout') != 2:
        return str(path.relative_to(payload / 'home'))
    for name in sorted(data['sources'], key=len, reverse=True):
        base = source(payload, name)
        if path == base or base in path.parents:
            return str(Path(name) / path.relative_to(base))
    raise ValueError('File is outside the declared source map: ' + str(path))


def checksum_path(payload, name):
    path = safe(name)
    if path.parts[0] in ('config', 'system') and manifest(payload).get('layout') == 2:
        return payload.parents[1] / path
    return payload / path


def inventory(payload):
    data = manifest(payload)
    if data.get('layout') == 2:
        root = payload.parents[1]
        for name in ('config', 'system'):
            if (root / name).is_symlink() or any(p.is_symlink() for p in (root / name).rglob('*')):
                raise ValueError('Shipped source cannot contain symlinks: ' + name)
        paths = [p for name in ('config', 'system') for p in (root / name).rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts]
        return {str(p.relative_to(root)): p for p in paths} | {'manifest.json': payload / 'manifest.json'}
    return {str(p.relative_to(payload)): p for p in payload.rglob('*')
            if p.is_file() and p.name != 'checksums.json' and '__pycache__' not in p.parts}


def checkout_for(target):
    """Recognize canonical managed source and old release layouts."""
    target = target.resolve()
    for parent in [target, *target.parents]:
        if (parent / '.git').exists() and (
                (parent / 'system') in target.parents or
                (parent / 'desktop/payload/home') in target.parents):
            return parent
    return None
