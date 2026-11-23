"""Exercise fullscreen power-menu routing by output."""
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
    def test_toggle_uses_focused_or_invoking_output(self):
        script = '''
const assert = require('node:assert/strict');
const NiriService = {focusedMonitor: {name: 'eDP-1'}};
const Quickshell = {screens: [{name: 'eDP-1'}, {name: 'DP-1'}]};
function host() {
    return {open: false, togglePopup() { this.open = !this.open; }};
}
const powerMenuButtons = {'eDP-1': host(), 'DP-1': host()};
''' + function_source('togglePowerMenuForActive') + '''
const internal = powerMenuButtons['eDP-1'];
const external = powerMenuButtons['DP-1'];
togglePowerMenuForActive();
assert.equal(internal.open, true);
assert.equal(external.open, false);
togglePowerMenuForActive();
assert.equal(internal.open, false);
togglePowerMenuForActive('DP-1');
assert.equal(external.open, true);
assert.equal(internal.open, false);
NiriService.focusedMonitor = null;
togglePowerMenuForActive();
assert.equal(internal.open, true);
'''
        result = subprocess.run(['node', '-e', script], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
