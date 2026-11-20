"""Check relevance against the shipped settings index using the actual search JS."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONTROLS = ROOT / 'system/apps/shell/modules/widgets/dashboard/controls'


class SettingsSearchTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required')
    def test_relevance(self):
        script = r'''
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const context = vm.createContext({Icons: new Proxy({}, {get: () => ''})});
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
const source = fs.readFileSync(process.argv[2], 'utf8');
const index = source.split('readonly property var staticItems: ')[1].split('\n\n    property var items:')[0].trim();
context.items = vm.runInContext(index, context);
function results(query) { context.query = query; return vm.runInContext('search(query, items)', context); }
function top(query, label) { assert.equal(results(query)[0]?.label, label, query); }
top('Sound', 'Sound');
top('  SOUND!  ', 'Sound');
top('wallpaper', 'Wallpaper');
top('auto fit', 'Wallpaper');
top('wireless', 'Network');
top('wi-fi', 'Network');
top('microphone', 'Sound');
top('hotkeys', 'Keyboard shortcuts');
top('transparncy', 'Transparency and blur');
top('tranpsarency', 'Transparency and blur');
top('how do I change my font size', 'Text & shape');
top('screen refresh', 'Display');
top('refresh screen', 'Display');
top('turn off animations', 'Motion');
assert.equal(results('screen banana').length, 0);
assert.equal(results('zzzzzz').length, 0);
assert.equal(results('   ').length, 0);
assert.equal(results('how do I change settings').length, 0);
context.items = [
 {label: 'Other', keywords: 'sound'},
 {label: 'Sound options'},
 {label: 'Sound'},
 {label: 'Unrelated', keywords: 'SOUND'}
];
assert.deepEqual(Array.from(results('sound'), item => item.label),
 ['Sound', 'Sound options', 'Other', 'Unrelated']);
assert.equal(context.items[0].score, undefined, 'Do not mutate the index');
'''
        subprocess.run(['node', '-e', script, str(CONTROLS / 'SettingsSearch.js'),
                        str(CONTROLS / 'SettingsIndex.qml')], check=True)


if __name__ == '__main__':
    unittest.main()
