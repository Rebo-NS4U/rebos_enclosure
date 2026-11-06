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

class HeadingText(HTMLText):
    """Heading-only image alternatives; decorative body images stay excluded."""
    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        if tag == 'img' and not self.hidden:
            self.parts.append(dict(attrs).get('alt', ''))

def read_epub_details(path):
    with zipfile.ZipFile(path) as archive:
        def read(name):
            if archive.getinfo(name).file_size > 100 * 1024 * 1024:
                raise ValueError('EPUB member is too large.')
            return archive.read(name)
        def resolve(base, href):
            return posixpath.normpath(posixpath.join(posixpath.dirname(base), unquote(href.split('#')[0])))
        container = ET.fromstring(read('META-INF/container.xml'))
        package = next(e.attrib['full-path'] for e in container.iter() if e.tag.endswith('rootfile'))
        opf = ET.fromstring(read(package))
        title = next((normalize(e.text or '') for e in opf.iter() if e.tag.endswith('}title') and e.text), Path(path).stem)
        manifest = {e.attrib['id']: e.attrib for e in opf.iter() if e.tag.endswith('}item')}
        labels = {}
        for entry in manifest.values():
            location = resolve(package, entry['href'])
            if entry.get('media-type') == 'application/x-dtbncx+xml':
                navigation = ET.fromstring(read(location))
                for point in navigation.iter():
                    if point.tag.rsplit('}', 1)[-1] != 'navPoint': continue
                    label = next((normalize(''.join(e.itertext())) for e in point if e.tag.rsplit('}', 1)[-1] == 'navLabel'), '')
                    target = next((e.get('src', '') for e in point if e.tag.rsplit('}', 1)[-1] == 'content'), '')
                    if target and label: labels.setdefault(resolve(location, target), label)
            elif 'nav' in entry.get('properties', '').split():
                navigation = ET.fromstring(read(location))
                for nav in navigation.iter():
                    if nav.tag.rsplit('}', 1)[-1] != 'nav': continue
                    kind = nav.get('{http://www.idpf.org/2007/ops}type', '').split()
                    if 'toc' not in kind: continue
                    for link in nav.iter():
                        if link.tag.rsplit('}', 1)[-1] == 'a' and link.get('href'):
                            label = normalize(''.join(link.itertext()))
                            if label: labels.setdefault(resolve(location, link.get('href')), label)
        sections = []
        size = 0
        for item in opf.iter():
            if not item.tag.endswith('}itemref') or item.get('linear') == 'no': continue
            entry = manifest[item.attrib['idref']]
            if entry.get('media-type') not in ('application/xhtml+xml', 'text/html'): continue
            member = resolve(package, entry['href'])
            raw = read(member).decode('utf-8-sig')
            parser = HTMLText(); parser.feed(raw)
            text = ''.join(parser.parts)
            size += len(text)
            if size > LIMIT: raise ValueError('Book exceeds 20 million characters.')
            heading = re.search(r'<h[1-3]\b[^>]*>(.*?)</h[1-3]>', raw, re.S | re.I)
            heading_text = HeadingText()
            if heading: heading_text.feed(heading.group(1))
            label = labels.get(member) or normalize(''.join(heading_text.parts)) or f'Section {len(sections) + 1}'
            sections.append((label, text))
    text, chapters = join_sections(sections)
    return text, chapters, title

def read_epub(path):
    text, chapters, _ = read_epub_details(path)
    return text, chapters

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
            CREATE TABLE IF NOT EXISTS book_catalogue (id TEXT PRIMARY KEY, title TEXT, chapters TEXT, size INTEGER, kind TEXT DEFAULT 'book');
            CREATE TABLE IF NOT EXISTS book_content (id TEXT PRIMARY KEY, text TEXT);
            CREATE TABLE IF NOT EXISTS app_state (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS book_progress (id TEXT PRIMARY KEY, position INTEGER DEFAULT 0, typed TEXT DEFAULT '', loops INTEGER DEFAULT 0, updated REAL);
        ''')

        self.db.execute('BEGIN IMMEDIATE')
        if 'kind' not in {row[1] for row in self.db.execute('PRAGMA table_info(book_catalogue)')}:
            self.db.execute("ALTER TABLE book_catalogue ADD COLUMN kind TEXT DEFAULT 'book'")
        if not self.db.execute("SELECT 1 FROM app_state WHERE key='practice_classified'").fetchone():
            # Classify previously saved built-in samples without touching real books.
            samples = Path(__file__).resolve().parent.parent / 'TypingTexts.js'
            if samples.exists():
                raw = samples.read_text()
                for sample in json.loads(raw[raw.index('['):].strip().rstrip(';')):
                    key = hashlib.sha256(normalize(sample['text']).encode()).hexdigest()
                    self.db.execute("UPDATE book_catalogue SET kind='practice' WHERE id=?", (key,))
            self.db.execute("INSERT INTO app_state VALUES ('practice_classified','1')")
        self.db.commit()

    def last_id(self):
        row = self.db.execute("SELECT c.id FROM app_state s JOIN book_catalogue c ON c.id=s.value WHERE s.key='last_book'").fetchone()
        if row: return row[0]
        row = self.db.execute("SELECT c.id FROM book_catalogue c JOIN book_progress p USING(id) ORDER BY (c.kind='book') DESC,p.updated DESC LIMIT 1").fetchone()
        return row[0] if row else None

    def activate(self, key):
        with self.db:
            self.db.execute("INSERT INTO app_state VALUES ('last_book',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key,))
            self.db.execute('UPDATE book_progress SET updated=? WHERE id=?', (time.time(), key))


    def add(self, title, text, chapters, kind="book"):
        if not text or len(text) > LIMIT: raise ValueError('Book must contain 1 to 20 million characters.')
        key = hashlib.sha256(text.encode()).hexdigest()
        with self.db:
            self.db.execute('INSERT INTO book_catalogue (id,title,chapters,size,kind) VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,chapters=excluded.chapters,size=excluded.size,kind=excluded.kind', (key, title[:160], json.dumps(chapters), len(text), kind))
            self.db.execute('INSERT OR IGNORE INTO book_content VALUES (?,?)', (key, text))
            self.db.execute('INSERT OR IGNORE INTO book_progress (id,updated) VALUES (?,?)', (key, time.time()))
        self.activate(key)
        return self.page(key)

    def listing(self):
        rows = self.db.execute('SELECT c.id,c.title,c.kind,c.size AS length,p.position,length(p.typed) AS partial,p.loops FROM book_catalogue c JOIN book_progress p ON p.id=c.id ORDER BY p.updated DESC')
        books = []
        for row in rows:
            data = dict(row)
            data['completion'] = 1.0 if data['loops'] else min(1.0, (data['position'] + data['partial']) / max(1, data['length']))
            books.append(data)
        return books

    def page(self, key, include_chapters=True):
        row = self.db.execute('SELECT c.id,c.title,c.kind,c.size AS length,c.chapters,p.position,p.typed,p.loops FROM book_catalogue c JOIN book_progress p ON p.id=c.id WHERE c.id=?', (key,)).fetchone()
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
            self.db.execute("INSERT INTO app_state VALUES ('last_book',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key,))

    def handle(self, request):
        action = request['action']
        if action == 'list': return {'books': self.listing(), 'last_id': self.last_id()}
        if action == 'resume':
            key = self.last_id()
            return self.page(key) if key else {'empty': True}
        if action == 'import':
            value = request['path']
            path = Path(unquote(urlparse(value).path) if value.startswith('file:') else value).expanduser()
            if path.stat().st_size > 100 * 1024 * 1024: raise ValueError('Choose a book under 100 MB.')
            if path.suffix.lower() == '.epub':
                text, chapters, title = read_epub_details(path)
            else:
                text, chapters = sections_document(extract_raw(str(path)))
                title = path.stem
            return self.add(title, text, chapters)
        if action == 'add':
            text, chapters = sections_document(request['text'])
            return self.add(request.get('title', 'Pasted text'), text, chapters, request.get('kind', 'book'))
        if action == 'open':
            page = self.page(request['id'])
            self.activate(request['id'])
            return page
        if action == 'chapter':
            current = self.page(request['id'])
            index = request['index']
            if not isinstance(index, int) or not 0 <= index < len(current['chapters']):
                raise ValueError('Choose a valid chapter.')
            self.save(request['id'], current['chapters'][index]['position'], '', request.get('loops', current['loops']))
            return self.page(request['id'])
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
