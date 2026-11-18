"""Render flat hardware keycaps and verify pressed and keyboard focus states."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

APP = Path(__file__).resolve().parents[2] / 'system/apps/shell'

class HardwareButtonTests(unittest.TestCase):
    def test_keycaps_render_and_change_state(self):
        if not shutil.which('qs'):
            self.skipTest('Requires Quickshell')
        with tempfile.TemporaryDirectory(prefix='hardware-buttons-') as directory:
            root = Path(directory)
            for name in ('modules', 'config', 'assets', 'scripts', 'version'):
                (root / name).symlink_to(APP / name)
            (root / 'runtime').mkdir(mode=0o700)
            (root / 'shell.qml').write_text('''import QtQuick
import QtQuick.Window
import Quickshell
import qs.config
import qs.modules.components
ShellRoot {
 Window { visible:true; width:360; height:160
  Row {
   ThemeButton { id: neutral; text:"Apply" }
   ThemeButton { id: action; text:"Save"; highlighted:true }
   ToggleButton { id: icon; buttonIcon:"+"; tooltipText:"Add"; onToggle:()=>{} }
  }
 }
 Timer { interval:200; running:true; repeat:true; property int step:0
  onTriggered: {
   Config.theme.shellStyle="terminal-hardware";
   if(step++===0)return;
   function check(ok) { if(!ok)throw new Error("HARDWARE_BUTTON_FAILED"); }
   if(step===2){
    check(neutral.background.controlSurface && action.background.controlSurface && icon.background.controlSurface);
    check(neutral.background.gradientStops.length===1 && action.background.gradientStops.length===1);
    neutral.down=true;icon.down=true;action.down=true;
    neutral.forceActiveFocus();return;
   }
   check(neutral.background.variant==="internalbg" && icon.background.variant==="internalbg");
   check(action.background.variant==="primaryfocus" && action.background.controlPressed);
   check(neutral.activeFocus && neutral.background.border.width===2);
   console.log("HARDWARE_BUTTON_OK");Qt.quit();
  }
 }
}''')
            env = dict(os.environ, HOME=directory, XDG_RUNTIME_DIR=str(root / 'runtime'),
                       QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='basic')
            for key in ('WAYLAND_DISPLAY','DISPLAY','DBUS_SESSION_BUS_ADDRESS','NIRI_SOCKET'):
                env.pop(key, None)
            result = subprocess.run(['qs','-p',str(root / 'shell.qml')],env=env,
                                    capture_output=True,text=True,timeout=12)
            output=result.stdout+result.stderr
            self.assertEqual(result.returncode,0,output)
            self.assertIn('HARDWARE_BUTTON_OK',output)
            for error in ('ReferenceError','TypeError','Unable to assign','Cannot assign','HARDWARE_BUTTON_FAILED'):
                self.assertNotIn(error,output)
