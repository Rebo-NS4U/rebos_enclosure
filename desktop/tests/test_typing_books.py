"""Book import, bounded page delivery, and durable progress regression tests."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'system/apps/shell/scripts'))
from typing_books import Library, read_epub, sections_document

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

if __name__ == '__main__': unittest.main()
