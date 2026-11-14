#!/usr/bin/env python3
"""Local launcher providers. Never execute query text or make network requests."""
import ast
import collections
import json
import math
import operator
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlencode, urlsplit

FUNCTIONS = {name: getattr(math, name) for name in
             ('sqrt', 'sin', 'cos', 'tan', 'log', 'log10', 'floor', 'ceil')}
FUNCTIONS.update(abs=abs, round=round)
BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
          ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
          ast.Mod: operator.mod, ast.Pow: operator.pow}


def calculate(expression):
    if len(expression) > 256:
        raise ValueError('Expression too long')
    tree = ast.parse(expression.replace('^', '**'), mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 80:
        raise ValueError('Expression too complex')

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
        elif isinstance(node, ast.Name) and node.id in ('pi', 'e', 'tau'):
            value = getattr(math, node.id)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and type(node.op) in BINARY:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError('Exponent too large')
            value = BINARY[type(node.op)](left, right)
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id in FUNCTIONS and not node.keywords and len(node.args) <= 2):
            value = FUNCTIONS[node.func.id](*(visit(arg) for arg in node.args))
        else:
            raise ValueError('Unsupported expression')
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e100:
            raise ValueError('Result out of range')
        return value

    return format(visit(tree.body), '.12g')


def row(kind, name, comment, target='', icon='system-search'):
    return dict(id='launcher:' + kind + ':' + target, name=name, comment=comment,
                icon=icon, execString='', categories=[], runInTerminal=False,
                kind=kind, target=target)


def file_results(term, home):
    """Bounded breadth-first name search; skip hidden/build trees and symlink dirs."""
    rows, pending = [], collections.deque([home])
    deadline, visited = time.monotonic() + 0.5, 0
    skip = {'node_modules', 'target', 'build', 'vendor', '__pycache__', 'go'}
    while pending and visited < 25000 and time.monotonic() < deadline:
        directory = pending.popleft()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    visited += 1
                    if visited >= 25000 or time.monotonic() >= deadline:
                        break
                    if entry.name.startswith('.') or entry.name in skip:
                        continue
                    if term.casefold() in entry.name.casefold():
                        path = Path(entry.path)
                        rows.append(row('open', entry.name, str(path), path.as_uri(),
                                        'folder' if entry.is_dir(follow_symlinks=False) else 'text-x-generic'))
                        if len(rows) >= 20:
                            return rows
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(Path(entry.path))
        except OSError:
            continue
    return rows


def search(query, home=None):
    text = query.strip()
    if not text:
        return []
    home = Path(home or Path.home())
    file_match = re.match(r'^files?\s+(.*)$', text, re.I)
    if file_match:
        term = file_match[1].strip()
        matches = file_results(term, home) if term else []
        return matches + [row('hint', 'File search: ' + ('20 results maximum' if len(matches) == 20 else 'bounded scan'),
                             'Bounded home scan; hidden and build folders excluded. Refine the name for more results.')]
    if text.startswith(('/', '~/')):
        path = Path(os.path.expanduser(text))
        return [row('open', path.name or str(path), str(path), path.as_uri(), 'folder')] if path.exists() else [row('hint', 'Path not found', str(path))]

    google = re.match(r'^(?:g|google)\s+(.*)$', text, re.I)
    calc = text.startswith('=')
    expression = text[1:].strip() if calc else text
    rows = []
    if calc or re.match(r'^(?:[\d.(+\-]|sqrt\(|sin\(|cos\(|tan\(|log\(|log10\(|abs\(|round\(|pi\b|tau\b)', expression):
        try:
            result = calculate(expression)
            rows.append(row('copy', '= ' + result, 'Calculator · Enter to copy result', result, 'accessories-calculator'))
        except (ValueError, SyntaxError, TypeError, ZeroDivisionError, OverflowError):
            if calc:
                rows.append(row('hint', 'Enter a valid calculation', 'Example: = sqrt(144) + 2^3'))
    if calc:
        return rows
    url = text if re.match(r'^https?://', text, re.I) else 'https://' + text
    try:
        parsed = urlsplit(url)
    except ValueError:
        parsed = urlsplit("https://www.google.com")
        url = ""
    is_host = bool(parsed.hostname and ('.' in parsed.hostname or parsed.hostname == 'localhost'))
    if url and not google and not re.search(r'\s', text) and is_host:
        if parsed.scheme in ('http', 'https'):
            rows.append(row('open', 'Open ' + text, 'Default browser', url, 'web-browser'))
    term = google[1].strip() if google else text
    if term:
        rows.append(row('open', 'Google: ' + term, 'Search in default browser',
                        'https://www.google.com/search?' + urlencode({'q': term}), 'web-browser'))
    return rows


if __name__ == '__main__':
    query = sys.argv[1] if len(sys.argv) > 1 else ''
    try:
        results = search(query)
    except (ValueError, OSError):
        results = [row('hint', 'Unable to read search', 'Check the address or file path')]
    print(json.dumps({'query': query, 'results': results}))
