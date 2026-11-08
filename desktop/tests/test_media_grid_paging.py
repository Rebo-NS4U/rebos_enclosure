"""Run the QML grid's paging calculation across viewport and scrolling changes."""
from pathlib import Path
import shutil
import subprocess
import unittest


class MediaGridPagingTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node required')
    def test_fills_viewport_after_first_page_resize_and_scroll(self):
        source = Path(__file__).resolve().parents[2] / 'system/apps/media/ui/MediaGridPaging.js'
        harness = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const context = {};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8').replace('.pragma library', ''), context);
const more = context.needsMore;
// Six columns, four visible rows: a 20-item YouTube page leaves a gap.
assert(more(20, 1440, 800, 240, 200, 0, 800, 100));
assert(!more(40, 1440, 800, 240, 200, 0, 1400, 100));
// Enlarging the window needs another page without any scrolling.
assert(more(40, 1440, 1400, 240, 200, 0, 1400, 100));
// Nine-column poster grid also fills its partial last row and one buffer row.
assert(more(30, 1440, 900, 160, 250, 0, 1000, 100));
assert(!more(54, 1440, 900, 160, 250, 0, 1500, 100));
// Continue loading when approaching the bottom; ignore overscroll above the top.
assert(more(60, 1440, 800, 240, 200, 1100, 2000, 200));
assert(!more(60, 1440, 800, 240, 200, -80, 2000, 200));
assert(!more(0, 0, 800, 240, 200, 0, 0, 100));
assert(!more(0, 1440, 0, 240, 200, 0, 0, 100));
assert(!more(0, 1440, 800, 0, 200, 0, 0, 100));
'''
        result = subprocess.run(['node', '-e', harness, str(source)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
