"""Render the production dialog and pairing controls across the shared theme matrix."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

APP = Path(__file__).resolve().parents[2] / 'system/apps/shell'
HARNESS = '''
import QtQuick
import QtTest
import Quickshell
import qs.config
import qs.modules.theme
import qs.modules.services
import qs.modules.widgets.dashboard.controls
ShellRoot {
 QtObject {
  id: controller
  property bool authenticating: false
  property var request: ({title:"Desktop selection", placeholder:"Search choices"})
  property var choices: ["Clipboard history", "Wi-Fi and Bluetooth", "Audio mixer"]
  property var flow: ({identities:[],isResponseRequired:true,responseVisible:false,message:"Authorize a desktop action",inputPrompt:"Password:",failed:false})
  property int cancelled: 0
  property int submitted: 0
  function cancel() { cancelled++; }
  function submit() { submitted++; }
  function finish(value) { submitted++; }
  function filter() {}
 }
 FloatingWindow {
  visible: true
  implicitWidth: 800; implicitHeight: 900
  DesktopDialogSurface { id: surface; x:32; y:32; width:Math.min(620,parent.width-64); height:Math.min(620,implicitHeight); controller:controller }
  BluetoothPairingPrompt { id: pairing; x:32; y:surface.y+surface.height+24; width:Math.min(400,parent.width-64) }
  TestCase { id: tester; when:false }
  Timer { interval:500; running:true; onTriggered: {
   try {
    Config.animDuration = 0;
    const styles = ["canopy","orbital","metropolis","monolith","blueprint","terminal-hardware","glass-vault","radar-station","suspended-film","frosted","colorful","clear-glass","custom"];
    let cases = 0;
    let previousImage = null;
    for (const light of [false,true]) {
     Colors.background=light?"#f4f0e8":"#101820";
     Colors.overBackground=light?"#202820":"#f4f4f4";
     Colors.primary=light?"#305838":"#a0d8b0";
     Colors.overPrimary=light?"#ffffff":"#101820";
     for (const style of styles) {
      Config.theme.shellStyle=style;
      for (const size of [14,24]) {
       Config.theme.fontSize=size;
       for (const radius of [0,16]) {
        Config.theme.roundness=radius;
        tester.wait(15);
        tester.compare(surface.radius,radius);
        tester.compare(surface.rectOpacity,Styling.getStyledRectConfig("popup").opacity);
        tester.compare(surface.searchInput.implicitHeight,Styling.spacing(48));
        surface.choiceList.currentIndex=0; surface.choiceList.forceLayout(); tester.wait(10);
        const button=surface.choiceList.itemAtIndex(0);
        tester.verify(button !== null);
        tester.compare(button.font.pixelSize,Styling.fontSize(-1));
        const label = button.contentItem.children.find(child => child.text === button.text);
        tester.verify(label !== undefined, "Choice label exists");
        tester.compare(label.color,button.background.itemColor);
        tester.compare(button.background.radius,radius);
        button.forceActiveFocus(); tester.wait(5);
        tester.verify(button.activeFocus);
        tester.compare(button.background.border.color,button.background.itemColor);
        tester.compare(button.background.border.width,2);
        surface.searchInput.focusInput(); tester.wait(5);
        tester.verify(surface.searchInput.inputActiveFocus);
        tester.compare(surface.searchInput.border.color,Colors.primary);
        cases++;
       }
      }
      if (!light) {
       Config.theme.fontSize=14; Config.theme.roundness=16; tester.wait(30);
       const image=tester.grabImage(surface);
       tester.verify(image.width>0 && image.height>0);
       if (Quickshell.env("DIALOG_THEME_NATIVE") === "1") {
        tester.compare(image.width,Math.round(surface.width));
        if (previousImage) tester.verify(!image.equals(previousImage),"Material rendering must change");
        previousImage=image;
       }
       const output=Quickshell.env("DIALOG_THEME_PREVIEW_DIR");
       if (output) image.save(output + "/" + style + ".png");
      }
      Config.theme.shellTransparency=35; tester.wait(5);
      tester.fuzzyCompare(surface.rectOpacity,0.65,0.001);
      Config.theme.shellTransparency=-1;
     }
    }
    controller.authenticating=true; tester.wait(30);
    tester.verify(surface.searchInput.passwordMode);
    tester.keyClick(Qt.Key_Escape); tester.compare(controller.cancelled,1);
    controller.flow={identities:[],isResponseRequired:false,responseVisible:false,message:"Waiting",inputPrompt:"Please wait",failed:true};
    tester.wait(20); tester.verify(!surface.searchInput.enabled);
    controller.authenticating=false; surface.width=260; surface.height=180;
    Config.theme.fontSize=28; tester.wait(40);
    tester.verify(surface.contentImplicitHeight>surface.height);
    BluetoothService.pairingAddress="preview";
    BluetoothService.pairingCode="000042";
    BluetoothService.pairingPrompt={kind:"RequestPinCode"}; tester.wait(30);
    tester.verify(pairing.visible && pairing.inputRequired);
    tester.verify(pairing.implicitHeight>0);
    console.log("DIALOG THEME MATRIX PASSED",cases); Qt.quit();
   } catch(e) { console.error(e); Qt.exit(1); }
  } }
 }
}
'''


class DialogThemeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
    def test_dialog_theme_matrix(self):
        with tempfile.TemporaryDirectory(prefix='enclosure-dialog-themes-') as temporary:
            root = Path(temporary)
            for name in ('modules', 'config', 'assets'):
                shutil.copytree(APP / name, root / name)
            shutil.copy2(APP / 'DesktopDialogSurface.qml', root)
            harness = HARNESS
            if os.environ.get('DIALOG_THEME_NATIVE') == '1':
                shutil.copy2(APP / 'DesktopDialogs.qml', root)
                harness = harness.replace('ShellRoot {', 'ShellRoot { Component { id: hostDefinition; DesktopDialogs {} }', 1)
            (root / 'shell.qml').write_text(harness)
            (root / 'runtime').mkdir(mode=0o700)
            env = dict(os.environ, HOME=temporary, XDG_RUNTIME_DIR=str(root / 'runtime'),
                       QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_QPA_PLATFORMTHEME='basic')
            if os.environ.get('DIALOG_THEME_NATIVE') == '1':
                env.update(QT_QPA_PLATFORM='wayland', XDG_RUNTIME_DIR=os.environ['XDG_RUNTIME_DIR'])
                env.pop('QT_QUICK_BACKEND', None)
                env.pop('DBUS_SESSION_BUS_ADDRESS', None)
            else:
                for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                    env.pop(key, None)
            for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
                env[key] = str(root / key)
            result = subprocess.run(['qs', '-p', temporary, '--no-color'], env=env,
                                    capture_output=True, text=True, timeout=35, cwd=root)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('DIALOG THEME MATRIX PASSED 104', output)
            self.assertNotIn('ReferenceError', output)
            self.assertNotIn('TypeError', output)


if __name__ == '__main__':
    unittest.main()
