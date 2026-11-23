"""Rendering themes preserves selected colors and application exports."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]

class CuratedThemeTests(unittest.TestCase):
    def test_saved_theme_selections(self):
        for app in ('shell', 'assistant'):
            with self.subTest(app=app):
                source = (ROOT / f'system/apps/{app}/config/ConfigValidator.js').read_text().replace('.pragma library', '')
                subprocess.run(['node', '-e', source + '''
const assert = require('node:assert/strict');
assert.equal(validate({shellStyle: 'nebula'}, {shellStyle: 'frosted'}).shellStyle, 'glyph');
for (const style of ['frosted-ceramic', 'suspended-film', 'circuit-glass', 'prism-glass', 'optical-instrument', 'guilloche']) {
 assert.equal(validate({shellStyle: style}, {shellStyle: 'frosted'}).shellStyle, 'guilloche');
}
'''], check=True)

    def test_palettes_and_exports(self):
        for app in ('shell', 'assistant', 'media/ui'):
            with self.subTest(app=app):
                source = (ROOT / f'system/apps/{app}/modules/theme/ShellStyles.js').read_text().replace('.pragma library', '')
                script = source + '''
const assert = require('node:assert/strict');
const ids = ['monolith','blueprint','terminal-hardware'];
assert.deepEqual(styles.slice(0,4).map(s=>s.id), ['canopy','orbital','glyph','metropolis']);
assert.deepEqual(styles.map(s => s.id).sort(), [...ids, 'frosted', 'colorful', 'glass-vault', 'radar-station', 'guilloche', 'canopy', 'orbital', 'glyph', 'metropolis', 'clear-glass'].sort());
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
assert.equal(surface('monolith', 'bg', p).gradient.length, 1);
assert.equal(surface('monolith', 'bg', p).radius, undefined);
assert.equal(surface('monolith', 'internalbg', p).gradient[0][0], p.background);
assert.equal(surface('blueprint', 'bg', p).radius, undefined);
assert.equal(surface('blueprint', 'primary', p).gradient[0][0], p.background);
for (const palette of palettes) {
 for (const role of ['bg','popup','bar','pane','surface','surfaceContainer','internalbg','focus','surfaceVariant','primary','secondary','tertiary']) {
  const material = surface('terminal-hardware', role, palette);
  assert.equal(material.gradient.length, 1, 'hardware must have a flat fill: ' + role);
 }
}
assert.equal(surface('terminal-hardware', 'bg', p).border[1], 2);
assert.equal(surface('terminal-hardware', 'primary', p).gradient.length, 1);
assert.equal(surface('terminal-hardware', 'internalbg', p).gradient[0][0], p.background);
for (let i = 0; i < ids.length; i++) for (let j = i + 1; j < ids.length; j++)
 assert.notDeepEqual(surface(ids[i], 'bg', p), surface(ids[j], 'bg', p));
const materials = ['glass-vault','radar-station','guilloche','clear-glass','canopy','orbital','metropolis'];
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
   assert.equal(s.gradient.length, 1, id + ' flat ' + role);
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
// Keep the base and text fixed so this isolates the wallpaper accents.
const changedAccents = {...p, primary:'#a9b4ff', tertiary:'#ffbadb'};
assert.equal(surface('glyph', 'bg', p).gradient[0][0], surface('glyph', 'bg', changedAccents).gradient[0][0]);
const glyph = {...p, background:'#000000', foreground:'#f2f2f2', primary:'#d71921'};
assert.equal(surface('glyph', 'surface', glyph).gradient[0][0], '#0e0e0e');
assert.equal(surface('glyph', 'surfaceContainer', glyph).gradient[0][0], '#1a1a1a');
assert.equal(surface('glyph', 'bg', glyph).border[0], '#2a2a2a');
assert.equal(themePalette('glyph'), null);
assert.equal(surface('glyph', 'bg', p).gradient[0][0], p.background);
assert.equal(surface('glyph', 'focus', changedAccents).border[0], changedAccents.primary);
assert.equal(surface('clear-glass', 'bg', p).opacity, 0.52);
assert.equal(surface('clear-glass', 'bg', p).radius, undefined);
assert.equal(surface('clear-glass', 'pane', p).border[1], 0);
assert.equal(surface('glass-vault', 'bg', p).radius, undefined);
assert.equal(surface('radar-station', 'bg', p).radius, undefined);
assert.equal(surface('guilloche', 'bg', p).radius, undefined);
assert.ok(surface('guilloche', 'bg', p).opacity > surface('guilloche', 'internalbg', p).opacity);
assert.equal(surface('guilloche', 'focus', p).border[0], p.primary);
for (let i=0; i<materials.length; i++) for (let j=i+1; j<materials.length; j++)
 assert.notDeepEqual(surface(materials[i], 'bg', p), surface(materials[j], 'bg', p));
// A neutral selected palette must stay neutral through every material theme.
// This catches fixed blue glass or amber accents leaking into palette-derived surfaces.
for (const {id} of styles) {
 const gray = {background:'#181818',foreground:'#eeeeee',primary:'#bbbbbb',secondary:'#aaaaaa',tertiary:'#999999'};
 for (const role of ['bg','popup','pane','internalbg','focus']) {
  const material = surface(id, role, gray);
  for (const color of [...material.gradient.map(stop => stop[0]),material.border[0]]) {
   const channels=color.slice(-6).match(/../g);
   assert.ok(channels.every(c => c === channels[0]), id + ' injected a hue into ' + role);
  }
 }
}
assert.equal(themePalette('custom'), null);
'''
                result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
