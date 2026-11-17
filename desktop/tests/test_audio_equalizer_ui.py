"""Exercise the real QML audio tab against a private, bypassed EQ service."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

APP = Path(__file__).resolve().parents[2] / 'system/apps/shell'
HARNESS = '''import QtQuick
import QtTest
import Quickshell
import qs.config
import qs.modules.components
import qs.modules.theme
import qs.modules.services
import qs.modules.widgets.dashboard.controls
ShellRoot {
 function find(item,name) {
  if(item.objectName===name) return item;
  for(const child of item.children || []) { const result=find(child,name); if(result) return result; }
  return null;
 }
 FloatingWindow {
  visible:true; implicitWidth:1000; implicitHeight:980
  StyledRect { id:previewSurface; anchors.fill:parent; variant:"bg"
  AudioMixerPanel { id:panel; x:24; y:24; width:parent.width-48; height:parent.height-48; currentSection:"equalizer" }
  }
  TestCase { id:tester; when:false }
  Timer { interval:600; running:true; onTriggered: {
   try {
    tester.tryCompare(AudioEqualizer,"initialized",true,5000);
    tester.compare(AudioEqualizer.enabled,false);
    Config.animDuration=0;
    const speech=find(panel,"audio-eq-preset-Speech");
    tester.verify(speech!==null && speech.visible);
    tester.mouseClick(speech); tester.wait(500);
    tester.compare(AudioEqualizer.preset,"Speech");
    tester.compare(AudioEqualizer.gains[0],-5);
    const band=find(panel,"audio-eq-band-0");
    tester.verify(band!==null); band.forceActiveFocus();
    tester.keyClick(Qt.Key_Right); tester.wait(500);
    tester.compare(AudioEqualizer.gains[0],-4.5);
    tester.compare(AudioEqualizer.preset,"Custom");
    for(const style of ["canopy","orbital","metropolis","monolith","blueprint","terminal-hardware","glass-vault","radar-station","suspended-film","frosted","colorful","clear-glass"]) {
     Config.theme.shellStyle=style; tester.wait(20);
     tester.compare(speech.contentItem.color,speech.background.itemColor);
     tester.verify(band.activeFocus);
    }
    Config.theme.shellStyle="orbital"; tester.wait(40);
    const destination=Quickshell.env("AUDIO_EQ_PREVIEW");
    if(destination) tester.grabImage(previewSurface).save(destination);
    panel.width=300; Config.theme.fontSize=24; tester.wait(50);
    tester.verify(find(panel,"audio-eq-toggle")!==null);
    console.log("AUDIO EQ UI PASSED"); Qt.quit();
   }catch(e){console.error(e);Qt.exit(1);}
  } }
 }
}'''


class EqualizerUiTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
    def test_audio_tab(self):
        with tempfile.TemporaryDirectory(prefix='enclosure-eq-ui-') as folder:
            root = Path(folder)
            for name in ('modules', 'config', 'assets'):
                shutil.copytree(APP/name, root/name)
            (root/'scripts').mkdir()
            for name in ('audio_equalizer.py', 'audio_eq_dsp.py'):
                shutil.copy2(APP/'scripts'/name, root/'scripts'/name)
            (root/'shell.qml').write_text(HARNESS)
            runtime = root/'runtime'
            runtime.mkdir(mode=0o700)
            env = dict(os.environ, HOME=folder, XDG_RUNTIME_DIR=str(runtime), QT_QPA_PLATFORM='offscreen',
                       QT_QUICK_BACKEND='software', QT_QPA_PLATFORMTHEME='basic', PULSE_SERVER='unix:'+str(root/'no-audio'))
            if os.environ.get('DIALOG_THEME_NATIVE') == '1':
                env.update(QT_QPA_PLATFORM='wayland', XDG_RUNTIME_DIR=os.environ['XDG_RUNTIME_DIR'])
                env.pop('QT_QUICK_BACKEND',None)
            else:
                for key in ('DISPLAY','WAYLAND_DISPLAY'):
                    env.pop(key,None)
            env.pop('DBUS_SESSION_BUS_ADDRESS',None)
            for key in ('XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_DATA_HOME','XDG_STATE_HOME'):
                env[key] = str(root/key)
            worker = subprocess.Popen(['python3', str(root/'scripts/audio_equalizer.py'), 'serve'],env=env,
                                      stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
            try:
                for _ in range(50):
                    if (Path(env['XDG_RUNTIME_DIR'])/'enclosure-audio-eq.sock').exists():break
                    time.sleep(.02)
                result = subprocess.run(['qs','-p',folder,'--no-color'],env=env,capture_output=True,text=True,timeout=20)
                output = result.stdout+result.stderr
                self.assertEqual(result.returncode,0,output)
                self.assertIn('AUDIO EQ UI PASSED',output)
                self.assertNotIn('ReferenceError',output)
                self.assertNotIn('TypeError',output)
                saved=json.loads((Path(env['XDG_CONFIG_HOME'])/'enclosure/audio-equalizer.json').read_text())
                self.assertEqual(saved['gains'][0],-4.5)
                self.assertFalse(saved['enabled'])
            finally:
                worker.terminate()
                worker.communicate(timeout=5)


if __name__ == '__main__':
    unittest.main()
