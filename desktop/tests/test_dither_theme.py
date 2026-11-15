"""Verify retired dithering falls back to clean opaque surfaces."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DitherThemeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required")
    def test_texture_and_controls(self):
        source = (ROOT / "system/apps/shell/modules/theme/ShellStyles.js").read_text().replace(".pragma library", "")
        script = source + """
const assert = require('node:assert/strict');
for (const light of [false, true]) {
 const p = {background:light?'#f5f5f5':'#101010', foreground:light?'#101010':'#eeeeee',
 primary:'#4585a0', onPrimary:'#ffffff', secondary:'#4585a0', onSecondary:'#ffffff',
 tertiary:'#4585a0', onTertiary:'#ffffff', error:'#a03030', onError:'#ffffff'};
 assert.ok(!styles.some(entry => entry.id === 'dithered'));
 let previous = 0;
 for (const strength of [0, 20, 50, 100]) {
  assert.equal(ditherCellSize(strength), 1);
  const panel = surface('dithered', 'bg', p, strength);
  assert.equal(panel.gradientType, 'linear');
  assert.deepEqual(panel, surface('quiet', 'bg', p, strength));
  assert.ok(contrast(panel.halftoneDotColor, panel.itemColor) >= 4.5);
  const difference = contrast(panel.halftoneDotColor, panel.halftoneBackgroundColor);
  assert.ok(difference >= previous);
  previous = difference;
  assert.equal(panel.border[1], 1);
  for (const role of ['primary','secondary','tertiary','error','primaryfocus']) {
   assert.equal(surface('dithered', role, p, strength).gradientType, 'linear');
  }
  assert.equal(surface('dithered','pane',p,strength).border[1], 0);
 }
}
"""
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
