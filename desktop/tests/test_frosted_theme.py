"""Frosted surface contrast, semantic actions and palette export."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]

class FrostedThemeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for theme functions')
    def test_glass_surfaces_and_semantic_actions(self):
        source = (ROOT/'system/apps/shell/modules/theme/ShellStyles.js').read_text().replace('.pragma library','')
        result = subprocess.run(['node','-e',source+'''
const assert = require('node:assert/strict');
assert.equal(styles.filter(s => s.id === 'frosted').length, 1);
for (const light of [false,true]) {
 const p = {background:light?'#f4f5f7':'#080b10',foreground:light?'#18202b':'#e3e8ef',primary:light?'#215b80':'#8cc9e8',onPrimary:light?'#ffffff':'#10202b',secondary:'#90b5ad',onSecondary:'#14221e',tertiary:'#bdafd5',onTertiary:'#231a30',error:'#ffb4ab',onError:'#690005'};
 const get = role => surface('frosted',role,p);
 for (const role of ['bg','popup','bar','pane','surface','surfaceContainer']) {
  assert.equal(get(role).opacity,0.68);
  assert.equal(get(role).gradient.length,3);
  assert.equal(get(role).border[1],1);
  for (const stop of get(role).gradient) assert.ok(contrast(stop[0],get(role).itemColor)>=4.5,role+' contrast');
 }
 assert.equal(get('common').opacity,0.48);
 assert.equal(get('focus').opacity,0.84);
 assert.equal(get('focus').border[0],p.primary);
 for (const role of ['primary','secondary','tertiary','error']) {
  assert.equal(get(role).opacity,1);
  assert.equal(get(role).gradient[0][0],p[role]);
  assert.equal(get(role).itemColor,p['on'+role[0].toUpperCase()+role.slice(1)]);
 }
 assert.equal(get('transparent').opacity,0);
 assert.equal(get('barbg').opacity,0);
 const palette = appPalette('frosted',{...p,overBackground:p.foreground,overPrimary:p.onPrimary,overSecondary:p.onSecondary,overTertiary:p.onTertiary,overError:p.onError},1);
 assert.equal(palette.opacity,0.68);
 assert.equal(palette.background,get('bg').gradient[0][0]);
 assert.equal(palette.surface,get('pane').gradient[0][0]);
}
'''],text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
