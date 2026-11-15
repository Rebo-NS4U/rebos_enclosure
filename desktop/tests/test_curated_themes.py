"""Rendering themes preserves selected colors and application exports."""
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
const ids = ['monolith','blueprint','terminal-hardware'];
assert.deepEqual(styles.slice(0,3).map(s=>s.id), ['glass-vault','radar-station','suspended-film']);
assert.deepEqual(styles.map(s => s.id).sort(), [...ids, 'frosted', 'colorful', 'glass-vault', 'radar-station', 'suspended-film', 'clear-glass'].sort());
assert.ok(!styles.some(s => ['botanical-archive','condensation','optical-instrument'].includes(s.id)));
for (const id of ids) {
 assert.ok(styles.some(s => s.id === id));
 assert.equal(themePalette(id), null);
}
const palettes = [
 {background:'#101820', foreground:'#f4f4f4', primary:'#a0d8b0', secondary:'#d8b0a0', tertiary:'#c8b0e0', error:'#ffb4ab', onPrimary:'#101820', onSecondary:'#101820', onTertiary:'#101820', onError:'#101820'},
 {background:'#f4f0e8', foreground:'#202820', primary:'#305838', secondary:'#684830', tertiary:'#584068', error:'#a02020', onPrimary:'#ffffff', onSecondary:'#ffffff', onTertiary:'#ffffff', onError:'#ffffff'}
];
for (const id of ids) {
 for (const p of palettes) {
  const original = JSON.stringify(p);
  const panel = surface(id, 'bg', p);
  assert.notDeepEqual(panel, surface('quiet', 'bg', p));
  assert.equal(panel.itemColor, p.foreground);
  assert.equal(panel.opacity, 1);
  for (const role of ['bg','popup','pane','internalbg','focus','primary','primaryfocus','secondary','tertiary','error']) {
   const s = surface(id, role, p);
   for (const stop of s.gradient) assert.ok(contrast(stop[0], s.itemColor) >= 4.5, id + ' ' + role);
  }
  for (const role of ['primary','secondary','tertiary','error']) {
   const control = surface(id, role, p);
   assert.equal(id === 'blueprint' ? control.itemColor : control.gradient[0][0], p[role]);
  }
  const exported = appPalette(id, {...p, overBackground:p.foreground, overPrimary:p.onPrimary, overSecondary:p.onSecondary, overTertiary:p.onTertiary, overError:p.onError}, 1);
  assert.equal(exported.background, panel.gradient[0][0]);
  assert.equal(exported.primary, p.primary);
  assert.equal(exported.overPrimary, p.onPrimary);
  for (const role of ['transparent','barbg']) assert.equal(surface(id, role, p).opacity, 0);
  assert.equal(JSON.stringify(p), original);
 }
 assert.notDeepEqual(surface(id, 'bg', palettes[0]), surface(id, 'bg', palettes[1]));
}
const p = palettes[0];
assert.equal(surface('monolith', 'bg', p).border[1], 0);
assert.equal(surface('monolith', 'bg', p).gradient.length, 6);
assert.equal(surface('monolith', 'bg', p).radius, undefined);
assert.equal(surface('monolith', 'internalbg', p).gradient[0][0], p.background);
assert.equal(surface('blueprint', 'bg', p).radius, undefined);
assert.equal(surface('blueprint', 'primary', p).gradient[0][0], p.background);
assert.equal(surface('terminal-hardware', 'bg', p).gradient.length, 4);
assert.equal(surface('terminal-hardware', 'bg', p).border[1], 2);
assert.equal(surface('terminal-hardware', 'primary', p).gradient.length, 5);
assert.equal(surface('terminal-hardware', 'internalbg', p).gradient[0][0], p.background);
for (let i = 0; i < ids.length; i++) for (let j = i + 1; j < ids.length; j++)
 assert.notDeepEqual(surface(ids[i], 'bg', p), surface(ids[j], 'bg', p));
const materials = ['glass-vault','radar-station','suspended-film','clear-glass'];
assert.equal(styles[styles.length - 1].id, 'clear-glass');
for (const id of materials) {
 assert.equal(themePalette(id), null);
 for (const palette of palettes) {
  const original = JSON.stringify(palette);
  const panel = surface(id, 'bg', palette);
  assert.ok(panel.opacity > 0 && panel.opacity < 1);
  for (const role of ['bg','popup','pane','surface','internalbg','focus']) {
   const s = surface(id, role, palette);
   assert.ok(s.opacity > 0 && s.opacity < 1);
   assert.equal(s.itemColor, palette.foreground);
   for (const stop of s.gradient) assert.ok(contrast(stop[0], s.itemColor) >= 4.5, id + ' ' + role);
  }
  for (const role of ['primary','secondary','tertiary','error']) {
   const s = surface(id, role, palette);
   assert.equal(s.gradient[0][0], palette[role]);
   assert.equal(s.opacity, 1);
  }
  for (const role of ['transparent','barbg']) assert.equal(surface(id, role, palette).opacity, 0);
  const exported = appPalette(id, {...palette, overBackground:palette.foreground, overPrimary:palette.onPrimary, overSecondary:palette.onSecondary, overTertiary:palette.onTertiary, overError:palette.onError}, 1);
  assert.equal(exported.opacity, panel.opacity);
  assert.equal(exported.primary, palette.primary);
  assert.equal(JSON.stringify(palette), original);
 }
 assert.notDeepEqual(surface(id, 'bg', palettes[0]), surface(id, 'bg', palettes[1]));
}
assert.equal(surface('clear-glass', 'bg', p).opacity, 0.52);
assert.equal(surface('clear-glass', 'bg', p).radius, undefined);
assert.equal(surface('clear-glass', 'pane', p).border[1], 0);
assert.equal(surface('glass-vault', 'bg', p).radius, undefined);
assert.equal(surface('radar-station', 'bg', p).radius, undefined);
assert.equal(surface('suspended-film', 'bg', p).radius, undefined);
for (let i=0; i<materials.length; i++) for (let j=i+1; j<materials.length; j++)
 assert.notDeepEqual(surface(materials[i], 'bg', p), surface(materials[j], 'bg', p));
assert.equal(themePalette('custom'), null);
'''
                result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
