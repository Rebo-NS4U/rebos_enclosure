"""Botanical rendering preserves selected colors and application exports."""
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
assert.equal(themePalette('botanical-archive'), null);
const palettes = [
 {background:'#101820', foreground:'#f4f4f4', primary:'#a0d8b0', secondary:'#d8b0a0', tertiary:'#c8b0e0', error:'#ffb4ab', onPrimary:'#101820', onSecondary:'#101820', onTertiary:'#101820', onError:'#101820'},
 {background:'#f4f0e8', foreground:'#202820', primary:'#305838', secondary:'#684830', tertiary:'#584068', error:'#a02020', onPrimary:'#ffffff', onSecondary:'#ffffff', onTertiary:'#ffffff', onError:'#ffffff'}
];
for (const p of palettes) {
 const original = JSON.stringify(p);
 const paper = surface('botanical-archive', 'bg', p);
 assert.notDeepEqual(paper, surface('quiet', 'bg', p));
 assert.equal(paper.gradient.length, 3);
 assert.equal(paper.radius, 10);
 assert.equal(paper.itemColor, p.foreground);
 assert.equal(surface('botanical-archive', 'internalbg', p).radius, 4);
 assert.equal(surface('botanical-archive', 'pane', p).border[1], 1);
 assert.equal(paper.opacity, 1);
 for (const role of ['bg','popup','pane','internalbg','focus','primary','secondary','tertiary','error']) {
  const s = surface('botanical-archive', role, p);
  for (const stop of s.gradient) assert.ok(contrast(stop[0], s.itemColor) >= 4.5, role);
 }
 for (const role of ['primary','secondary','tertiary','error'])
  assert.equal(surface('botanical-archive', role, p).gradient[0][0], p[role]);
 const exported = appPalette('botanical-archive', {...p, overBackground:p.foreground, overPrimary:p.onPrimary, overSecondary:p.onSecondary, overTertiary:p.onTertiary, overError:p.onError}, 1);
 assert.equal(exported.background, paper.gradient[0][0]);
 assert.equal(exported.primary, p.primary);
 assert.equal(exported.overPrimary, p.onPrimary);
 assert.equal(surface('botanical-archive', 'transparent', p).opacity, 0);
 assert.equal(JSON.stringify(p), original);
}
assert.notDeepEqual(surface('botanical-archive', 'bg', palettes[0]), surface('botanical-archive', 'bg', palettes[1]));
assert.equal(themePalette('custom'), null);
'''
                result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
