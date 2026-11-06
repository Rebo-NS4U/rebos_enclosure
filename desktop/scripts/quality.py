#!/usr/bin/env python3
"""Check design diagnostics and prevent documented exceptions from growing."""
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tokenize

ROOT = Path(__file__).resolve().parents[2]
RULES = 'design,duplicate-code'


def scan(root, *, raw=False):
    rules = RULES if raw else RULES + ',useless-suppression'
    result = subprocess.run(
        [sys.executable, '-m', 'pylint', '--recursive=y', '--disable=all',
         '--enable=' + rules, '--reports=n', '--score=n', '--output-format=json',
         'desktop/scripts', 'system'], cwd=root, capture_output=True, text=True, check=False)
    if result.returncode & 35:
        raise RuntimeError('Pylint failed: ' + result.stderr[:1000] + result.stdout[:1000])
    return json.loads(result.stdout)


def without_exceptions(source):
    tokens = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT and 'pylint:' in token.string and 'disable' in token.string:
            token = token._replace(string='')
        tokens.append(token)
    return tokenize.untokenize(tokens)


def copy_python_sources(root, target):
    for relative in ('desktop/scripts', 'system'):
        for source in (root / relative).rglob('*.py'):
            if '__pycache__' in source.parts:
                continue
            destination = target / source.relative_to(root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(without_exceptions(source.read_text()))


def diagnostic_key(item):
    return item['path'], item.get('obj', item.get('object', '')), item['symbol']


def check_ceilings(diagnostics, exceptions):
    approved = {diagnostic_key(item): item for item in exceptions}
    seen, errors = set(), []
    for item in diagnostics:
        key = diagnostic_key(item)
        seen.add(key)
        rule = approved.get(key)
        quantity = re.search(r'\((\d+)/\d+\)', item['message'])
        if rule is None or quantity is None:
            errors.append('New warning: ' + repr(key))
            continue
        observed, ceiling = int(quantity[1]), rule['ceiling']
        worse = observed < ceiling if item['symbol'] == 'too-few-public-methods' else observed > ceiling
        if worse:
            errors.append(f'Exception grew: {key}: {observed} versus {ceiling}')
    errors.extend('Remove obsolete exception: ' + repr(key) for key in approved.keys() - seen)
    return errors


def main():
    normal = scan(ROOT)
    if normal:
        for item in normal:
            print(item['path'], item['obj'], item['symbol'], item['message'])
        return 1
    exceptions = json.loads((ROOT / 'desktop/quality-exceptions.json').read_text())['exceptions']
    with tempfile.TemporaryDirectory(prefix='enclosure-quality-') as folder:
        temporary = Path(folder)
        copy_python_sources(ROOT, temporary)
        raw = scan(temporary, raw=True)
    errors = check_ceilings(raw, exceptions)
    if errors:
        print('\n'.join(errors))
        return 1
    print(f'Design check passed: no active warnings; {len(exceptions)} documented exceptions remain within their ceilings.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
