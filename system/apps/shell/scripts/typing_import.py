#!/usr/bin/env python3
"""Extract document text locally; never execute document content."""
import html.parser
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlparse
import zipfile
import xml.etree.ElementTree as ET

class HTMLText(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)
        if tag in ('p', 'div', 'br'): self.parts.append(' ')
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)

def extract(value):
    path = Path(unquote(urlparse(value).path) if value.startswith('file:') else value).expanduser()
    if path.stat().st_size > 30 * 1024 * 1024:
        raise ValueError('Choose a document under 30 MB.')
    suffix = path.suffix.lower()
    if suffix == '.pdf':
        result = subprocess.run(['pdftotext', '-enc', 'UTF-8', str(path.resolve()), '-'], capture_output=True, timeout=30)
        if result.returncode: raise ValueError('Could not read PDF. It may be encrypted.')
        text = result.stdout.decode('utf-8')
    elif suffix in ('.docx', '.odt'):
        member = 'word/document.xml' if suffix == '.docx' else 'content.xml'
        with zipfile.ZipFile(path) as archive:
            if archive.getinfo(member).file_size > 20 * 1024 * 1024:
                raise ValueError('Document text is too large.')
            tree = ET.fromstring(archive.read(member))
        text = ' '.join(''.join(p.itertext()) for p in tree.iter() if p.tag.rsplit('}', 1)[-1] in ('p', 'h'))
    elif suffix in ('.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm', '.log'):
        text = path.read_text(encoding='utf-8-sig')
        if suffix in ('.html', '.htm'):
            parser = HTMLText(); parser.feed(text); text = ' '.join(parser.parts)
        elif suffix == '.xml': text = ' '.join(ET.fromstring(text).itertext())
    else:
        raise ValueError('Supported: PDF, DOCX, ODT, HTML, XML, TXT, Markdown, CSV, JSON and LOG.')
    text = ' '.join(text.split())
    if not text: raise ValueError('No text found. Scanned PDFs need OCR first.')
    if len(text) > 1000000: raise ValueError('Choose a document with under one million characters.')
    return text

if __name__ == '__main__':
    try: print(json.dumps({'text': extract(sys.argv[1])}))
    except Exception as error: print(json.dumps({'error': str(error)}))
