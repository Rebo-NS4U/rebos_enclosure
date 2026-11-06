"""Book import, bounded page delivery, and durable progress regression tests."""
import json
import sqlite3
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'system/apps/shell/scripts'))
from typing_books import Library, read_epub, read_epub_details, sections_document

class Books(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'library.sqlite3'
        self.library = Library(self.path)

    def tearDown(self):
        self.library.db.close()
        self.temp.cleanup()

    def test_large_book_bounded_pages_and_durable_resume(self):
        text, chapters = sections_document('Chapter One\n' + ('A quiet line with many words. ' * 150000) + '\nChapter Eleven\nThe end.')
        first = self.library.add('A long book', text, chapters)
        self.assertGreater(first['length'], 1000000)
        self.assertEqual(len(first['chapters']), 2)
        key = first['id']
        offset = len(text) - 100
        saved = self.library.handle({'action': 'seek', 'id': key, 'position': offset})
        self.library.save(key, saved['position'], 'A mistype', 2)
        self.library.db.close()
        self.library = Library(self.path)
        restored = self.library.page(key)
        self.assertEqual(restored['typed'], 'A mistype')
        self.assertEqual(restored['position'], saved['position'])
        self.assertEqual(restored['loops'], 2)
        next_page = self.library.handle({'action': 'next', 'id': key, 'position': restored['position'] + len(restored['passage'])})
        self.assertLessEqual(len(next_page['passage']), 90)
        self.assertNotIn('chapters', next_page)
        self.assertNotIn('text', next_page)
        self.assertLess(len(json.dumps(next_page)), 1200)
        self.assertEqual(len(self.library.listing()), 1)
        # Re-importing an unchanged book preserves its saved location.
        self.assertEqual(self.library.add('Duplicate', text, chapters)['position'], next_page['position'])

    def test_bookmarks_do_not_reload_or_rewrite_book_content(self):
        book = self.library.add('Stable content', 'A short sentence. ' * 10000, [{'title': 'Beginning', 'position': 0}])
        cached = self.library.cached_text
        statements = []
        self.library.db.set_trace_callback(statements.append)
        for position in range(0, 900, 90):
            self.library.handle({'action': 'next', 'id': book['id'], 'position': position})
        self.assertIs(self.library.cached_text, cached)
        self.assertFalse(any('book_content' in query for query in statements))
        self.assertTrue(any('UPDATE book_progress' in query for query in statements))

    def test_heading_offsets_unicode_and_loop(self):
        text, chapters = sections_document('Chapter One\nHello 😀 world.\nChapter Two\nGoodbye.')
        self.assertEqual(text[chapters[1]['position']:], 'Chapter Two Goodbye.')
        book = self.library.add('Unicode', text, chapters)
        self.assertIn('😀', book['passage'])
        self.library.handle({'action': 'next', 'id': book['id'], 'position': 0, 'loops': 1})
        self.assertEqual(self.library.page(book['id'])['loops'], 1)
        with self.assertRaises(ValueError): self.library.save(book['id'], len(text), '', 0)

    def test_epub_spine_order_and_hidden_content(self):
        path = Path(self.temp.name) / 'book.epub'
        with zipfile.ZipFile(path, 'w') as book:
            book.writestr('META-INF/container.xml', '<container><rootfile full-path="OPS/book.opf"/></container>')
            book.writestr('OPS/book.opf', '<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="a" href="a.xhtml" media-type="application/xhtml+xml"/><item id="b" href="b.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="b"/><itemref idref="a"/></spine></package>')
            book.writestr('OPS/a.xhtml', '<html><head><title>Hidden title</title></head><body><h1>Second</h1><p>Last page.</p></body></html>')
            book.writestr('OPS/b.xhtml', '<h1>First</h1><p>Hel<b>lo</b> world.</p><script>secret</script>')
        text, chapters = read_epub(path)
        self.assertEqual([row['title'] for row in chapters], ['First', 'Second'])
        self.assertEqual(text, 'First Hello world. Second Last page.')
        self.assertEqual(text[chapters[1]['position']:], 'Second Last page.')
        self.assertEqual(self.library.handle({'action': 'import', 'path': str(path)})['chapters'], chapters)

    def test_image_headings_ncx_metadata_and_refresh_preserve_position(self):
        path = Path(self.temp.name) / 'unhelpful-file-name.epub'
        with zipfile.ZipFile(path, 'w') as book:
            book.writestr('META-INF/container.xml', '<container><rootfile full-path="OPS/book.opf"/></container>')
            book.writestr('OPS/book.opf', '<package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/"><metadata><dc:title>Readable book title</dc:title></metadata><manifest><item id="a" href="a.xhtml" media-type="application/xhtml+xml"/><item id="b" href="b.xhtml" media-type="application/xhtml+xml"/><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>')
            book.writestr('OPS/toc.ncx', '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"><navMap><navPoint><navLabel><text>Chapter 1</text></navLabel><content src="a.xhtml#start"/></navPoint><navPoint><navLabel><text>Chapter 2</text></navLabel><content src="b.xhtml#start"/></navPoint></navMap></ncx>')
            book.writestr('OPS/a.xhtml', '<h1><img alt="" src="one.png"/></h1><p>First original practice passage.</p>')
            book.writestr('OPS/b.xhtml', '<h1><img alt="Wrong scanned label" src="two.png"/></h1><p>Second original practice passage.</p>')
        text, chapters, title = read_epub_details(path)
        self.assertEqual(title, 'Readable book title')
        self.assertEqual([chapter['title'] for chapter in chapters], ['Chapter 1', 'Chapter 2'])
        old = self.library.add('Filename', text, [{'title': '', 'position': 0}])
        self.library.save(old['id'], 3, 'rs', 2)
        refreshed = self.library.add(title, text, chapters)
        self.assertEqual((refreshed['position'], refreshed['typed'], refreshed['loops']), (3, 'rs', 2))
        self.assertEqual(refreshed['id'], old['id'])
        jumped = self.library.handle({'action': 'chapter', 'id': old['id'], 'index': 1})
        self.assertEqual(jumped['passage'], 'Second original practice passage.')
        self.assertEqual(jumped['position'], chapters[1]['position'])
        with self.assertRaises(ValueError): self.library.handle({'action': 'chapter', 'id': old['id'], 'index': 99})

    def test_epub3_navigation_and_image_alt_fallback(self):
        path = Path(self.temp.name) / 'book.epub'
        with zipfile.ZipFile(path, 'w') as book:
            book.writestr('META-INF/container.xml', '<container><rootfile full-path="book.opf"/></container>')
            book.writestr('book.opf', '<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="a" href="a.xhtml" media-type="application/xhtml+xml"/><item id="b" href="b.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>')
            book.writestr('nav.xhtml', '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><nav epub:type="toc"><a href="a.xhtml">Opening chapter</a></nav></html>')
            book.writestr('a.xhtml', '<p>Opening text.</p>')
            book.writestr('b.xhtml', '<h1><img alt="Chapter 2"/></h1><p>Closing text.</p>')
        text, chapters = read_epub(path)
        self.assertEqual([chapter['title'] for chapter in chapters], ['Opening chapter', 'Chapter 2'])
        self.assertEqual(text, 'Opening text. Closing text.')

    def test_last_opened_resume_and_completion_survive_restart(self):
        first = self.library.add('First', 'a' * 100, [{'title': 'Start', 'position': 0}])
        second = self.library.add('Second', 'b' * 200, [{'title': 'Start', 'position': 0}])
        self.library.save(first['id'], 50, 'aa', 0)
        self.library.handle({'action': 'open', 'id': second['id']})
        self.library.db.close()
        self.library = Library(self.path)
        self.assertEqual(self.library.handle({'action': 'resume'})['id'], second['id'])
        rows = {book['id']: book for book in self.library.listing()}
        self.assertEqual(rows[first['id']]['completion'], 0.52)
        self.library.save(second['id'], 0, '', 1)
        self.assertEqual({book['id']: book for book in self.library.listing()}[second['id']]['completion'], 1)
        sample = self.library.add('A sample', 'practice text', [{'title': 'Sample', 'position': 0}], 'practice')
        self.assertEqual(self.library.page(sample['id'])['kind'], 'practice')
        self.assertEqual(self.library.handle({'action': 'resume'})['id'], sample['id'])

    def test_resume_empty_library(self):
        self.assertEqual(self.library.handle({'action': 'resume'}), {'empty': True})

    def test_upgrade_preserves_existing_book_and_partial_position(self):
        path = Path(self.temp.name) / 'legacy.sqlite3'
        old = sqlite3.connect(path)
        old.executescript("CREATE TABLE book_catalogue (id TEXT PRIMARY KEY,title TEXT,chapters TEXT,size INTEGER); CREATE TABLE book_content(id TEXT PRIMARY KEY,text TEXT); CREATE TABLE book_progress(id TEXT PRIMARY KEY,position INTEGER,typed TEXT,loops INTEGER,updated REAL);")
        old.execute('INSERT INTO book_catalogue VALUES (?,?,?,?)', ('legacy', 'Existing book', '[{"title":"Beginning","position":0}]', 100))
        old.execute('INSERT INTO book_content VALUES (?,?)', ('legacy', 'a' * 100))
        old.execute('INSERT INTO book_progress VALUES (?,?,?,?,?)', ('legacy', 40, 'aa', 0, 1))
        old.commit(); old.close()
        upgraded = Library(path)
        page = upgraded.handle({'action': 'resume'})
        self.assertEqual((page['id'], page['position'], page['typed'], page['kind']), ('legacy', 40, 'aa', 'book'))
        self.assertEqual(upgraded.listing()[0]['completion'], 0.42)
        upgraded.db.close()

if __name__ == '__main__': unittest.main()
