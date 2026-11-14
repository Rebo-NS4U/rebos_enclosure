"""Hostile document imports must fail before decompression or durable library edits."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'system/apps/shell/scripts'))
import typing_books
from typing_import import extract


class DocumentLimitTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def epub(self, repeats=1):
        path = self.root / 'compressed.epub'
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('META-INF/container.xml', '<container><rootfile full-path="book.opf"/></container>')
            archive.writestr('book.opf', '<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="a" href="a.xhtml" media-type="application/xhtml+xml"/></manifest><spine>' + '<itemref idref="a"/>' * repeats + '</spine></package>')
            archive.writestr('a.xhtml', '<html><script>' + 'hidden data ' * 100 + '</script><p>Visible text</p></html>')
        return path

    def test_cumulative_decompression_budget_applies_to_repeated_hidden_content(self):
        path = self.epub(10)
        before = path.read_bytes()
        with patch.object(typing_books, 'MAX_EPUB_BYTES', 4000):
            with self.assertRaisesRegex(ValueError, 'import budget'):
                typing_books.read_epub_details(path)
        self.assertEqual(path.read_bytes(), before)
        text, _, _ = typing_books.read_epub_details(self.epub(1))
        self.assertEqual(str(text), 'Visible text')

    def test_oversized_member_is_refused_before_reading_it(self):
        path = self.epub()
        original = zipfile.ZipFile.read
        read_members = []
        def checked_read(archive, name, *args, **kwargs):
            read_members.append(name)
            return original(archive, name, *args, **kwargs)
        with patch.object(typing_books, 'MAX_EPUB_BYTES', 600), patch.object(zipfile.ZipFile, 'read', checked_read):
            with self.assertRaisesRegex(ValueError, 'import budget'):
                typing_books.read_epub_details(path)
        self.assertNotIn('a.xhtml', read_members)

    def test_entity_expansion_is_rejected_and_external_entities_are_not_read(self):
        path = self.root / 'hostile.xml'
        entities = ['<!ENTITY a "' + 'x' * 1000 + '">']
        for index, name in enumerate('bcde', 1):
            entities.append('<!ENTITY ' + name + ' "' + ('&' + 'abcde'[index - 1] + ';') * 10 + '">')
        path.write_text('<!DOCTYPE root [' + ''.join(entities) + ']><root>&e;</root>')
        with self.assertRaises(ET.ParseError):
            extract(str(path))
        secret = self.root / 'private.txt'
        secret.write_text('must not be included')
        path.write_text('<!DOCTYPE root [<!ENTITY external SYSTEM "' + secret.as_uri() + '">]><root>&external;</root>')
        with self.assertRaises(ET.ParseError):
            extract(str(path))
        self.assertEqual(secret.read_text(), 'must not be included')

    def test_failed_import_preserves_existing_books_progress_and_preferences(self):
        library = typing_books.Library(self.root / 'library.sqlite3')
        self.addCleanup(library.db.close)
        book = library.add('Existing book', 'a familiar sentence ' * 10, [])
        library.save(book['id'], 4, 'draft', 1)
        before = library.handle({'action': 'open', 'id': book['id']})
        path = self.epub(10)
        with patch.object(typing_books, 'MAX_EPUB_BYTES', 4000):
            with self.assertRaises(ValueError):
                library.handle({'action': 'import', 'path': str(path)})
        self.assertEqual(library.db.execute('SELECT count(*) FROM book_catalogue').fetchone()[0], 1)
        self.assertEqual(library.handle({'action': 'open', 'id': book['id']}), before)
