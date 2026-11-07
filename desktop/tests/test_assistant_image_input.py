"""Verify clipboard routing without losing normal text paste."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const start = source.indexOf('                        function pasteClipboardTypes(text) {');
const end = source.indexOf('                        function removeAttachment', start);
assert(start >= 0 && end > start);
const context = {clipboardImageProcess: {}, clipboardUrisProcess: {},
    inputField: {paste() {this.pastes = (this.pastes || 0) + 1;}}};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
context.pasteClipboardTypes('text/plain\nimage/png\n');
assert.equal(context.clipboardImageProcess.mimeType, 'image/png');
assert.equal(context.clipboardImageProcess.running, true);
assert.equal(context.inputField.pastes, undefined);
context.pasteClipboardTypes('text/plain\ntext/uri-list');
assert.equal(context.clipboardUrisProcess.running, true);
assert.equal(context.inputField.pastes, undefined);
context.pasteClipboardTypes('text/plain;charset=utf-8\ntext/plain');
assert.equal(context.inputField.pastes, 1);
context.pasteClipboardTypes('');
assert.equal(context.inputField.pastes, 2);
'''


class ImageInputTest(unittest.TestCase):
    def test_clipboard_routes(self):
        for app in ('assistant', 'shell'):
            path = ROOT / 'system/apps' / app / 'modules/sidebar/AssistantSidebar.qml'
            with self.subTest(app=app):
                result = subprocess.run(['node', '-e', SCENARIO, str(path)],
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
