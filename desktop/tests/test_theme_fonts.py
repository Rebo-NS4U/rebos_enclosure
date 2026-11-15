"""Theme typography and custom-font preservation."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]

class ThemeFontTests(unittest.TestCase):
    def test_style_fonts(self):
        for app in ('shell', 'assistant'):
            source = (ROOT / f'system/apps/{app}/modules/theme/ShellStyles.js').read_text().replace('.pragma library', '')
            result = subprocess.run(['node', '-e', source + """
const assert = require('node:assert/strict');
const builtins = styles.filter(s => s.id !== 'custom');
for (const s of builtins) assert.ok(fontForStyle(s.id, 'User Font') !== 'User Font');
if (styles.some(s => s.id === 'instrument')) assert.equal(fontForStyle('instrument', 'User Font'), 'JetBrains Mono');
if (styles.some(s => s.id === 'frosted')) assert.equal(fontForStyle('frosted', 'User Font'), 'DejaVu Sans Mono');
assert.equal(fontForStyle('custom', 'User Font'), 'User Font');
assert.equal(fontForStyle('unknown', 'User Font'), 'User Font');
"""], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
