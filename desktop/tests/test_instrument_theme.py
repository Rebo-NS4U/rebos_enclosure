"""Check instrument surface depth, readable text and application exports."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]

class InstrumentThemeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for theme functions')
    def test_surface_hierarchy_and_exports(self):
        source = (ROOT / 'system/apps/shell/modules/theme/ShellStyles.js').read_text().replace('.pragma library', '')
        script = source + '''
const assert = require('node:assert/strict');
for (const light of [false, true]) {
 const p = {background: light ? '#f4f5f7' : '#080b10', foreground: light ? '#18202b' : '#e3e8ef', primary: light ? '#215b80' : '#8cc9e8', onPrimary: light ? '#ffffff' : '#10202b', secondary:'#90b5ad', onSecondary:'#14221e', tertiary:'#bdafd5', onTertiary:'#231a30', error:'#ffb4ab', onError:'#690005'};
 const get = role => surface('instrument', role, p);
 const colors = ['internalbg','bg','pane','focus'].map(role => get(role).gradient[0][0]);
 assert.equal(new Set(colors).size, 4, 'Depth levels must remain distinct');
 for (const role of ['internalbg','bg','popup','pane','common','focus']) {
  assert.equal(get(role).opacity, 1);
  assert.ok(contrast(get(role).gradient[0][0], get(role).itemColor) >= 4.5, role + ' text contrast');
 }
 assert.equal(get('transparent').opacity, 0);
 assert.equal(get('barbg').opacity, 0);
 assert.notEqual(get('focus').border[0], get('bg').border[0]);
 const exported = appPalette('instrument', {...p, overBackground:p.foreground, overPrimary:p.onPrimary, overSecondary:p.onSecondary, overTertiary:p.onTertiary, overError:p.onError}, 1);
 assert.equal(exported.surfaceContainer, get('pane').gradient[0][0]);
 assert.equal(exported.background, get('bg').gradient[0][0]);
}
'''
        result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
