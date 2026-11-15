"""Exercise power-menu routing across the initial layer-focus update."""
from pathlib import Path
import shutil
import subprocess
import unittest

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/shell/modules/services/Visibilities.qml'


def function_source(name):
    source = SOURCE.read_text()
    start = source.index('    function ' + name + '(')
    end = source.index('\n    }', start) + len('\n    }')
    return source[start:end]


class PowerMenuTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node required')
    def test_first_open_survives_focus_refresh(self):
        script = '''
const assert = require('node:assert/strict');
const Config = {bar: {style: 'island'}};
const NiriService = {focusedMonitor: {name: 'eDP-1'}};
let currentActiveModule = '', lastFocusedScreen = '';
const island = {
    isExpanded: false, currentMode: 'collapsed',
    expand(mode) { this.currentMode = mode; this.isExpanded = true; },
    collapse() { this.currentMode = 'collapsed'; this.isExpanded = false; }
};
function getIslandForActive() { return island; }
function clearAll() { island.collapse(); }
function applyActiveModuleToScreen() {}
''' + function_source('togglePowerMenuForActive') + function_source('moveActiveModuleToFocusedScreen') + '''
togglePowerMenuForActive();
assert.equal(island.currentMode, 'power');
// Niri publishes a fresh monitor object when the layer gains focus.
NiriService.focusedMonitor = {name: 'eDP-1'};
moveActiveModuleToFocusedScreen();
assert.equal(island.currentMode, 'power');
assert.equal(island.isExpanded, true);
togglePowerMenuForActive();
assert.equal(island.isExpanded, false);
'''
        result = subprocess.run(['node', '-e', script], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
