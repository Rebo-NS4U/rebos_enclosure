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

    def test_continuous_typing_windows_remain_bounded_and_overlap(self):
        text = 'word 😀 ' * 2000 + 'Next chapter'
        boundary = len(text) - len('Next chapter')
        book = self.library.add('Long chapters', text, [
            {'title': 'First', 'position': 0}, {'title': 'Next', 'position': boundary}])
        page = self.library.handle({'action': 'open', 'id': book['id'], 'window': 4096})
        self.assertLessEqual(len(page['passage']), 4096)
        offset = 2000
        typed = page['passage'][offset:3000]
        following = self.library.handle({'action': 'next', 'id': book['id'],
            'position': offset, 'typed': typed, 'window': 4096})
        self.assertLessEqual(len(following['passage']), 4096)
        self.assertEqual(following['typed'], typed)
        self.assertTrue(following['passage'].startswith(typed))
        last = self.library.handle({'action': 'next', 'id': book['id'],
            'position': boundary - 1000, 'typed': '', 'window': 4096})
        self.assertEqual(last['passage'], text[boundary - 1000:boundary])

    def test_paragraph_pages_preserve_identity_and_saved_progress(self):
        raw = "First paragraph ends here.\n\nSecond paragraph continues here."
        book = self.library.handle({'action': 'add', 'text': raw, 'window': 4096, 'paragraphs': True})
        self.assertEqual(book['passage'], 'First paragraph ends here. ')
        first_end = len(book['passage'])
        page = self.library.handle({'action': 'next', 'id': book['id'], 'position': first_end, 'typed': 'Sec', 'paragraphs': True, 'window': 4096})
        self.assertEqual(page['passage'], 'Second paragraph continues here.')
        self.library.db.close()
        self.library = Library(self.path)
        restored = self.library.handle({'action': 'open', 'id': book['id'], 'paragraphs': True, 'window': 4096})
        self.assertEqual((restored['position'], restored['typed']), (first_end, 'Sec'))
        imported = self.library.handle({'action': 'add', 'text': raw, 'paragraphs': True, 'window': 4096})
        self.assertEqual(imported['id'], book['id'])
        self.assertEqual(imported['position'], first_end)
        previous = self.library.handle({'action': 'previous', 'id': book['id'], 'position': first_end, 'paragraphs': True, 'window': 4096})
        self.assertEqual((previous['previousStart'], previous['previousText']), (0, book['passage']))

    def test_document_heading_variants_and_offsets(self):
        headings = ['Prologue', 'CHAPTER XXIV — Arrival', 'Chapter Twenty-One',
                    'Part 2: Winter', 'IV', '12. The Return', '###### Finale ######',
                    'Epilogue: Home']
        raw = '\n\n'.join(h + '\n\nA body paragraph with emoji 😀.' for h in headings)
        text, chapters = sections_document(raw)
        self.assertEqual([c['title'] for c in chapters],
                         headings[:6] + ['Finale', headings[7]])
        for chapter, original in zip(chapters, headings):
            self.assertTrue(text[chapter['position']:].startswith(original))

    def test_prose_toc_and_unisolated_numbers_are_not_headings(self):
        raw = ('Chapter One\nBody text.\n'
               'Chapter titles are sometimes misleading.\n'
               'Chapter 2 ........ 14\nChapter 3    27\n'
               'We counted\n12\nitems.\n'
               'Introduction to the subject is ordinary prose.\n')
        text, chapters = sections_document(raw)
        self.assertEqual([c['title'] for c in chapters], ['Chapter One'])
        self.assertIn('Chapter titles are', text)

    def test_word_notes_are_book_scoped_durable_and_preserve_reading(self):
        first = self.library.add('First', 'A character named Macy.', [])
        second = self.library.add('Second', 'Another Macy.', [])
        self.library.save(first['id'], 2, 'char', 1)
        before = tuple(self.library.db.execute('SELECT * FROM book_progress WHERE id=?', (first['id'],)).fetchone())
        saved = self.library.handle({'action': 'note', 'id': first['id'], 'term': '  MACY  ', 'note': 'A character.\nKeep this reminder.'})
        self.assertEqual(saved['term'], 'macy')
        self.assertEqual(saved['terms'], ['macy'])
        self.assertEqual(self.library.handle({'action': 'word', 'id': second['id'], 'term': 'Macy'})['note'], '')
        self.assertEqual(before, tuple(self.library.db.execute('SELECT * FROM book_progress WHERE id=?', (first['id'],)).fetchone()))
        self.library.db.close()
        self.library = Library(self.path)
        self.assertEqual(self.library.handle({'action': 'word', 'id': first['id'], 'term': 'Macy'})['note'], saved['note'])
        with self.assertRaises(ValueError):
            self.library.handle({'action': 'note', 'id': first['id'], 'term': 'Macy', 'note': 'x' * 10001})
        with self.assertRaises(ValueError):
            self.library.handle({'action': 'word', 'id': 'missing', 'term': 'Macy'})
        self.library.handle({'action': 'note', 'id': first['id'], 'term': 'Macy', 'note': ''})
        self.assertEqual(self.library.handle({'action': 'words', 'id': first['id']})['terms'], [])

    def test_dictionary_can_be_disabled_and_stays_disabled(self):
        self.assertTrue(self.library.handle({'action': 'word_settings'})['enabled'])
        self.assertFalse(self.library.handle({'action': 'word_settings', 'enabled': False})['enabled'])
        self.library.db.close()
        self.library = Library(self.path)
        self.assertFalse(self.library.handle({'action': 'word_settings'})['enabled'])
        self.assertTrue(self.library.handle({'action': 'word_settings', 'enabled': True})['enabled'])

    def test_reading_windows_stop_exactly_at_chapter_boundaries(self):
        text, chapters = sections_document('Chapter One\nHello 😀 world.\nChapter Two\nNext passage.')
        book = self.library.add('Chapter transitions', text, chapters)
        boundary = chapters[1]['position']
        self.assertEqual(book['passage'], text[:boundary])
        self.library.save(book['id'], boundary - 3, '', 0)
        self.assertEqual(self.library.page(book['id'])['passage'], text[boundary - 3:boundary])
        self.library.save(book['id'], boundary, '', 0)
        page = self.library.page(book['id'])
        self.assertEqual(page['passage'], 'Chapter Two Next passage.')
        self.assertEqual(page['position'], boundary)

    def test_categorized_notebook_entries_survive_reimport_and_restart(self):
        book = self.library.add('Notebook', 'The story begins here.', [])
        other = self.library.add('Other', 'A different story.', [])
        before = tuple(self.library.db.execute('SELECT * FROM book_progress WHERE id=?', (book['id'],)).fetchone())
        for category in ('People', 'Settings', 'Mysteries', 'Plot', 'General'):
            self.library.handle({'action': 'note', 'id': book['id'], 'term': category + ' title', 'note': 'Details and connections.', 'category': category})
        entries = self.library.handle({'action': 'words', 'id': book['id']})['entries']
        self.assertEqual({entry['category'] for entry in entries}, {'People', 'Settings', 'Mysteries', 'Plot', 'General'})
        self.assertEqual(self.library.handle({'action': 'words', 'id': other['id']})['entries'], [])
        self.assertEqual(before, tuple(self.library.db.execute('SELECT * FROM book_progress WHERE id=?', (book['id'],)).fetchone()))
        with self.assertRaises(ValueError):
            self.library.handle({'action': 'note', 'id': book['id'], 'term': 'Bad', 'note': 'Unchanged', 'category': 'Invalid'})
        self.library.add('Notebook', 'The story begins here.', [])
        self.library.db.close()
        self.library = Library(self.path)
        self.assertEqual(self.library.handle({'action': 'word', 'id': book['id'], 'term': 'People title'})['category'], 'People')
        self.library.handle({'action': 'note', 'id': book['id'], 'term': 'People title', 'note': 'A new clue.', 'category': 'Mysteries'})
        self.assertEqual(self.library.handle({'action': 'word', 'id': book['id'], 'term': 'People title'})['category'], 'Mysteries')

    def test_existing_word_notes_migrate_to_general_without_loss(self):
        path = Path(self.temp.name) / 'old-notes.sqlite3'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE word_notes (book_id TEXT,term TEXT,note TEXT NOT NULL,PRIMARY KEY(book_id,term))')
            db.execute('INSERT INTO word_notes VALUES (?,?,?)', ('old', 'macy', 'Original personal note.'))
        upgraded = Library(path)
        row = upgraded.db.execute('SELECT note,category FROM word_notes WHERE book_id=?', ('old',)).fetchone()
        self.assertEqual(tuple(row), ('Original personal note.', 'General'))
        upgraded.db.close()

    def test_delete_book_requires_confirmation_and_removes_only_its_local_data(self):
        first = self.library.add('Remove', 'A first story.', [])
        second = self.library.add('Keep', 'A second story.', [])
        self.library.handle({'action': 'note', 'id': first['id'], 'term': 'story', 'note': 'First note'})
        self.library.handle({'action': 'note', 'id': second['id'], 'term': 'story', 'note': 'Keep note', 'category': 'People'})
        self.library.handle({'action': 'open', 'id': first['id']})
        with self.assertRaises(ValueError):
            self.library.handle({'action': 'delete', 'id': first['id']})
        self.assertEqual(len(self.library.listing()), 2)
        deleted = self.library.handle({'action': 'delete', 'id': first['id'], 'confirmed': True})
        self.assertEqual(deleted['last_id'], second['id'])
        for table, column in [('book_catalogue', 'id'), ('book_content', 'id'), ('book_progress', 'id'), ('word_notes', 'book_id')]:
            self.assertEqual(self.library.db.execute(f'SELECT COUNT(*) FROM {table} WHERE {column}=?', (first['id'],)).fetchone()[0], 0)
        self.assertEqual(self.library.handle({'action': 'word', 'id': second['id'], 'term': 'story'})['note'], 'Keep note')
        self.library.db.close()
        self.library = Library(self.path)
        self.assertEqual(self.library.handle({'action': 'resume'})['id'], second['id'])
        self.library.handle({'action': 'delete', 'id': second['id'], 'confirmed': True})
        self.assertEqual(self.library.handle({'action': 'resume'}), {'empty': True})
        self.assertEqual(self.library.listing(), [])

    def test_previous_context_and_exact_durable_restore(self):
        text = '😀 first word. ' * 100
        book = self.library.add('Backward test', text, [])
        key = book['id']
        self.library.save(key, 137, '', 1)
        context = self.library.handle({'action': 'previous', 'id': key, 'position': 137, 'window': 4096})
        self.assertEqual(context['previousText'], text[:137])
        self.assertEqual(self.library.page(key)['position'], 137)
        restored = self.library.handle({'action': 'previous', 'id': key, 'resolved': True, 'position': 2, 'typed': 'wrong text', 'loops': 0})
        self.assertEqual(restored['position'], 2)  # Do not snap to the next word.
        self.assertEqual(restored['typed'], 'wrong text')
        self.assertTrue(self.library.handle({'action': 'previous', 'id': key, 'position': 0, 'loops': 0})['atBeginning'])
        wrapped = self.library.handle({'action': 'previous', 'id': key, 'position': 0, 'loops': 1, 'window': 4096})
        self.assertEqual(wrapped['previousText'], text)
        self.assertEqual(wrapped['loops'], 0)
        self.library.db.close()
        self.library = Library(self.path)
        self.assertEqual(self.library.page(key)['position'], 2)
        self.assertEqual(self.library.page(key)['typed'], 'wrong text')

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
        statements = []
        self.library.db.set_trace_callback(statements.append)
        for position in range(0, 900, 90):
            self.library.handle({'action': 'next', 'id': book['id'], 'position': position})
        reads = [query for query in statements if 'FROM book_content' in query]
        self.assertTrue(reads)
        self.assertTrue(all('SELECT substr(text,' in query for query in reads))
        self.assertFalse(any(query.startswith(('UPDATE book_content', 'INSERT INTO book_content')) for query in statements))
        self.assertTrue(any('UPDATE book_progress' in query for query in statements))

    def test_small_windows_preserve_unicode_and_every_character(self):
        text = 'A 😀 quoted “sentence” with narrow iii and wide WWW. ' * 100
        book = self.library.add('Paged', text, [])
        position, pieces = 0, []
        while position < len(text):
            page = self.library.handle({'action': 'next', 'id': book['id'],
                'position': position, 'window': 512})
            self.assertLessEqual(len(page['passage']), 512)
            self.assertTrue(page['passage'])
            pieces.append(page['passage'])
            position += len(page['passage'])
        self.assertEqual(''.join(pieces), text)

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
        self.assertEqual(text.paragraph_starts, [0, 6, 19, 26])
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

    def test_multiple_anchored_chapters_keep_text_and_bookmarks(self):
        for epub3 in (False, True):
            with self.subTest(epub3=epub3):
                path = Path(self.temp.name) / 'anchors.epub'
                targets = [('a.xhtml#first', 'Now'), ('a.xhtml#deux%20%C3%A9', 'Then'),
                           ('b.xhtml#third', 'Now'), ('b.xhtml#missing', 'Broken')]
                if epub3:
                    nav = ('<html xmlns:epub="http://www.idpf.org/2007/ops"><nav epub:type="toc">'
                           + ''.join(f'<a href="{href}">{label}</a>' for href, label in reversed(targets))
                           + '</nav></html>')
                    nav_item = '<item id="toc" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
                    nav_path = 'OPS/nav.xhtml'
                else:
                    nav = ('<ncx><navMap>' + ''.join(
                        f'<navPoint><navLabel><text>{label}</text></navLabel><content src="{href}"/></navPoint>'
                        for href, label in reversed(targets)) + '</navMap></ncx>')
                    nav_item = '<item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
                    nav_path = 'OPS/toc.ncx'
                with zipfile.ZipFile(path, 'w') as book:
                    book.writestr('META-INF/container.xml', '<container><rootfile full-path="OPS/book.opf"/></container>')
                    book.writestr('OPS/book.opf', '<package xmlns="http://www.idpf.org/2007/opf"><manifest>'
                                  '<item id="a" href="a.xhtml" media-type="application/xhtml+xml"/>'
                                  '<item id="b" href="b.xhtml" media-type="application/xhtml+xml"/>'
                                  + nav_item + '</manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>')
                    book.writestr(nav_path, nav)
                    book.writestr('OPS/a.xhtml', '<head><title id="hidden">Hidden</title></head>'
                                  '<p id="first">Now 😀 &amp; here.</p><a name="deux é"></a>'
                                  '<p>Then and there.</p>')
                    book.writestr('OPS/b.xhtml', '<p>Continuation of Then.</p><p id="third">Now again.</p>')
                text, chapters = read_epub(path)
                self.assertEqual(text, 'Now 😀 & here. Then and there. Continuation of Then. Now again.')
                self.assertEqual([c['title'] for c in chapters], ['Now', 'Then', 'Now'])
                self.assertEqual([text[c['position']:] for c in chapters],
                                 [text, 'Then and there. Continuation of Then. Now again.', 'Now again.'])
                old = self.library.add('Old metadata', text, [{'title': 'Old', 'position': 0}])
                self.library.save(old['id'], 4, '😀', 2)
                refreshed = self.library.add('New metadata', text, chapters)
                self.assertEqual(refreshed['id'], old['id'])
                self.assertEqual((refreshed['position'], refreshed['typed'], refreshed['loops']), (4, '😀', 2))
                self.assertEqual(self.library.handle({'action': 'chapter', 'id': old['id'], 'index': 2})['passage'], 'Now again.')

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

    def test_fullscreen_window_and_long_bookmark(self):
        book = self.library.add('Fullscreen', 'word ' * 2000, [])
        page = self.library.handle({'action': 'open', 'id': book['id'], 'window': 4096})
        self.assertGreater(len(page['passage']), 1000)
        self.assertLessEqual(len(page['passage']), 4096)
        typed = page['passage'][:1500]
        self.library.handle({'action': 'save', 'id': book['id'], 'position': 0, 'typed': typed})
        resumed = self.library.handle({'action': 'resume', 'window': 4096})
        self.assertEqual(resumed['typed'], typed)
        self.assertEqual(resumed['position'], 0)
        compact = self.library.handle({'action': 'open', 'id': book['id']})
        self.assertLessEqual(len(compact['passage']), 90)
        self.assertEqual(compact['typed'], typed)

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
