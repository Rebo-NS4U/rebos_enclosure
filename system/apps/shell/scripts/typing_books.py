#!/usr/bin/env python3
"""Local book library and bounded typing windows. JSON lines on stdin/stdout."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import sqlite3
import sys
import time
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET
import zipfile
from typing_import import HTMLText, extract_raw

LIMIT = 20000000
WINDOW = 90

def normalize(text):
    # Remove soft hyphens and PDF line-break hyphenation before flattening.
    text = re.sub(r'(\w)-[ \t]*\n[ \t]*(\w)', r'\1\2', text)
    return ' '.join(text.replace('\u00ad', '').split())

def sections_document(raw):
    sections = []
    current = []
    title = 'Beginning'
    for line in raw.splitlines():
        heading = re.match(r'^\s*(?:#{1,3}\s+.+|(?:chapter|part|book)\s+[0-9a-z].*)$', line, re.I)
        if heading and len(line) < 160:
            if current: sections.append((title, '\n'.join(current)))
            title = line.strip().lstrip('#').strip()
            current = []
        current.append(line)
    if current: sections.append((title, '\n'.join(current)))
    return join_sections(sections)

def join_sections(sections):
    chunks, chapters = [], []
    offset = 0
    for title, raw in sections:
        text = normalize(raw)
        if not text: continue
        chapters.append({'title': title[:160], 'position': offset})
        chunks.append(text)
        offset += len(text) + 1
        if offset > LIMIT + 1: raise ValueError('Book exceeds 20 million characters.')
    if not chunks: raise ValueError('No readable text found. Scanned PDFs need OCR first.')
    return ' '.join(chunks), chapters

def read_epub(path):
    with zipfile.ZipFile(path) as archive:
        def read(name):
            if archive.getinfo(name).file_size > 100 * 1024 * 1024:
                raise ValueError('EPUB member is too large.')
            return archive.read(name)
        container = ET.fromstring(read('META-INF/container.xml'))
        package = next(e.attrib['full-path'] for e in container.iter() if e.tag.endswith('rootfile'))
        opf = ET.fromstring(read(package))
        manifest = {e.attrib['id']: e.attrib for e in opf.iter() if e.tag.endswith('}item')}
        sections = []
        size = 0
        for item in opf.iter():
            if not item.tag.endswith('}itemref') or item.get('linear') == 'no': continue
            entry = manifest[item.attrib['idref']]
            if entry.get('media-type') not in ('application/xhtml+xml', 'text/html'): continue
            member = posixpath.normpath(str(PurePosixPath(package).parent / unquote(entry['href'].split('#')[0])))
            raw = read(member).decode('utf-8-sig')
            parser = HTMLText(); parser.feed(raw)
            text = ''.join(parser.parts)
            size += len(text)
            if size > LIMIT: raise ValueError('Book exceeds 20 million characters.')
            heading = re.search(r'<h[1-3]\b[^>]*>(.*?)</h[1-3]>', raw, re.S | re.I)
            label = HTMLText(); label.feed(heading.group(1) if heading else f'Section {len(sections) + 1}')
            sections.append((normalize(''.join(label.parts)), text))
    return join_sections(sections)

class Library:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.cached_id = None
        self.cached_text = ""
        # Keep large immutable content separate: saving a bookmark never rewrites a book.
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS book_catalogue (id TEXT PRIMARY KEY, title TEXT, chapters TEXT, size INTEGER);
            CREATE TABLE IF NOT EXISTS book_content (id TEXT PRIMARY KEY, text TEXT);
            CREATE TABLE IF NOT EXISTS book_progress (id TEXT PRIMARY KEY, position INTEGER DEFAULT 0, typed TEXT DEFAULT '', loops INTEGER DEFAULT 0, updated REAL);
        ''')

    def add(self, title, text, chapters):
        if not text or len(text) > LIMIT: raise ValueError('Book must contain 1 to 20 million characters.')
        key = hashlib.sha256(text.encode()).hexdigest()
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO book_catalogue VALUES (?,?,?,?)', (key, title[:160], json.dumps(chapters), len(text)))
            self.db.execute('INSERT OR IGNORE INTO book_content VALUES (?,?)', (key, text))
            self.db.execute('INSERT OR IGNORE INTO book_progress (id,updated) VALUES (?,?)', (key, time.time()))
        return self.page(key)

    def listing(self):
        return [dict(row) for row in self.db.execute('SELECT c.id,c.title,c.size AS length,p.position,p.loops FROM book_catalogue c JOIN book_progress p ON p.id=c.id ORDER BY p.updated DESC')]

    def page(self, key, include_chapters=True):
        row = self.db.execute('SELECT c.id,c.title,c.size AS length,c.chapters,p.position,p.typed,p.loops FROM book_catalogue c JOIN book_progress p ON p.id=c.id WHERE c.id=?', (key,)).fetchone()
        if row is None: raise ValueError('Book is no longer in the library.')
        data = dict(row)
        if self.cached_id != key:
            self.cached_text = self.db.execute('SELECT text FROM book_content WHERE id=?', (key,)).fetchone()[0]
            self.cached_id = key
        chunk = self.cached_text[data['position']:data['position'] + WINDOW]
        boundary = chunk.rfind(' ')
        if data['position'] + WINDOW < data['length'] and boundary > 40: chunk = chunk[:boundary + 1]
        data['passage'] = chunk
        if include_chapters: data['chapters'] = json.loads(data['chapters'])
        else: data.pop('chapters')
        return data

    def save(self, key, position, typed, loops):
        row = self.db.execute('SELECT size FROM book_catalogue WHERE id=?', (key,)).fetchone()
        if row is None: raise ValueError('Book is no longer in the library.')
        if not isinstance(position, int) or not 0 <= position < row[0]: raise ValueError('Invalid book position.')
        with self.db:
            self.db.execute('UPDATE book_progress SET position=?,typed=?,loops=?,updated=? WHERE id=?', (position, typed[:WINDOW], max(0, int(loops)), time.time(), key))

    def handle(self, request):
        action = request['action']
        if action == 'list': return {'books': self.listing()}
        if action == 'import':
            value = request['path']
            path = Path(unquote(urlparse(value).path) if value.startswith('file:') else value).expanduser()
            if path.stat().st_size > 100 * 1024 * 1024: raise ValueError('Choose a book under 100 MB.')
            text, chapters = read_epub(path) if path.suffix.lower() == '.epub' else sections_document(extract_raw(str(path)))
            return self.add(path.stem, text, chapters)
        if action == 'add':
            text, chapters = sections_document(request['text'])
            return self.add(request.get('title', 'Pasted text'), text, chapters)
        if action == 'open': return self.page(request['id'])
        if action in ('save', 'seek', 'next'):
            if action == 'seek':
                self.page(request['id'], False)
                position = request['position']
                if 0 < position < len(self.cached_text) and self.cached_text[position - 1] != ' ':
                    boundary = self.cached_text.find(' ', position, position + 40)
                    if boundary >= 0: request['position'] = min(boundary + 1, len(self.cached_text) - 1)
            self.save(request['id'], request['position'], request.get('typed', ''), request.get('loops', 0))
            return self.page(request['id'], action != 'next') if action != 'save' else {'saved': True}
        raise ValueError('Unknown library action.')

def main():
    os.umask(0o077)
    base = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    library = Library(base / 'rebos_shell/typing-books/library.sqlite3')
    for line in sys.stdin:
        request = {}
        try:
            parsed = json.loads(line)
            if not isinstance(parsed, dict): raise ValueError('Expected a request object.')
            request = parsed
            result = library.handle(request)
        except Exception as error:
            result = {'error': str(error)}
        print(json.dumps(dict(result, action=request.get('action'), request=request.get('request'))), flush=True)

if __name__ == '__main__': main()
