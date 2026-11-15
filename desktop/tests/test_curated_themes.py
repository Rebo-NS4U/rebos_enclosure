"""Curated theme readability, preview independence and application exports."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]

class CuratedThemeTests(unittest.TestCase):
    def test_palettes_and_exports(self):
        for app in ('shell', 'assistant', 'media/ui'):
            with self.subTest(app=app):
                source = (ROOT / f'system/apps/{app}/modules/theme/ShellStyles.js').read_text().replace('.pragma library', '')
                script = source + '''
const assert = require('node:assert/strict');
assert.deepEqual(Object.keys(curatedPalettes), ['botanical-archive']);
const botanical = themePalette('botanical-archive');
const paper = surface('botanical-archive', 'bg', {});
assert.notDeepEqual(paper, surface('quiet', 'bg', botanical));
assert.equal(paper.gradient.length, 3);
assert.equal(paper.radius, 10);
assert.equal(surface('botanical-archive', 'internalbg', {}).radius, 4);
assert.equal(surface('botanical-archive', 'pane', {}).border[1], 1);
assert.equal(paper.opacity, 1);
for (const id of Object.keys(curatedPalettes)) {
 const p = themePalette(id);
 assert.ok(styles.find(s => s.id === id));
 for (const role of ['bg','popup','pane','internalbg','focus','primary','secondary','tertiary','error']) {
  const s = surface(id, role, {});
  assert.ok(contrast(s.gradient[0][0], s.itemColor) >= 4.5, id + ' ' + role);
  assert.deepEqual(s, surface(id, role, {background:'#ffffff'}));
 }
 const exported = appPalette(id, p, 1);
 assert.equal(exported.background, surface(id, 'bg', p).gradient[0][0]);
 assert.equal(exported.overPrimary, p.overPrimary);
 assert.equal(surface(id, 'transparent', p).opacity, 0);
}
assert.equal(themePalette('custom'), null);
'''
                result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
