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
    const selector=find(panel,"audio-eq-presets");
    const nextPage=find(panel,"audio-eq-next-page");
    const previousPage=find(panel,"audio-eq-previous-page");
    tester.compare(selector.currentPage,0);
    tester.verify(!previousPage.enabled && nextPage.enabled);
    nextPage.forceActiveFocus(); tester.keyClick(Qt.Key_Space); tester.wait(100);
    tester.compare(selector.currentPage,1);
    previousPage.forceActiveFocus(); tester.keyClick(Qt.Key_Space); tester.wait(100);
    tester.compare(selector.currentPage,0);
    let speech=find(panel,"audio-eq-preset-Pop");
    tester.verify(speech!==null && speech.visible);
    speech.forceActiveFocus(); tester.keyClick(Qt.Key_End); tester.wait(60);
    tester.compare(selector.currentPage,selector.pageCount-1);
    tester.keyClick(Qt.Key_Home); tester.wait(60);
    tester.compare(selector.currentPage,0);
    speech=find(panel,"audio-eq-preset-Pop");
    tester.mouseClick(speech); tester.wait(500);
    tester.compare(AudioEqualizer.preset,"Pop");
    tester.compare(AudioEqualizer.gains[0],2);
    const band=find(panel,"audio-eq-band-0");
    tester.verify(band!==null); band.forceActiveFocus();
    tester.keyClick(Qt.Key_Up); tester.wait(500);
    tester.compare(AudioEqualizer.gains[0],2.5);
    tester.compare(AudioEqualizer.preset,"Custom");
    for(const style of ["canopy","orbital","metropolis","monolith","blueprint","terminal-hardware","glass-vault","radar-station","frosted-ceramic","frosted","colorful","clear-glass"]) {
     Config.theme.shellStyle=style; tester.wait(20);
     tester.compare(find(speech,"preset-card-label").color,speech.background.itemColor);
     tester.verify(band.activeFocus);
    }
    find(panel,"audio-eq-category-Other").forceActiveFocus(); tester.keyClick(Qt.Key_Space); tester.wait(40);
    const youtube=find(panel,"audio-eq-preset-YouTube"); tester.verify(youtube!==null);
    youtube.forceActiveFocus(); tester.keyClick(Qt.Key_Space); tester.wait(500);
    tester.compare(AudioEqualizer.preset,"YouTube"); tester.compare(AudioEqualizer.gains[0],-2);
    find(panel,"audio-eq-category-Extreme").forceActiveFocus(); tester.keyClick(Qt.Key_Space); tester.wait(40);
    tester.compare(selector.category,"Extreme");
    const extreme=find(panel,"audio-eq-preset-Pop Extreme"); tester.verify(extreme!==null);
    extreme.forceActiveFocus(); tester.keyClick(Qt.Key_Space); tester.wait(500);
    tester.compare(AudioEqualizer.preset,"Pop Extreme"); tester.compare(AudioEqualizer.gains[0],6);
    tester.compare(AudioEqualizer.error,"");
    find(panel,"audio-eq-category-Music").forceActiveFocus(); tester.keyClick(Qt.Key_Space); tester.wait(40);
    AudioEqualizer.selectPreset("Pop"); AudioEqualizer.setBand(0,2.5); tester.wait(500);
    Config.theme.shellStyle="orbital"; tester.wait(40);
    const destination=Quickshell.env("AUDIO_EQ_PREVIEW");
    if(destination) tester.grabImage(previewSurface).save(destination);
    panel.width=300; Config.theme.fontSize=24; tester.wait(50);
    tester.verify(find(panel,"audio-eq-toggle")!==null);
    console.log("AUDIO EQ UI PASSED"); Qt.quit();
   }catch(e){console.error(e, e.stack);Qt.exit(1);}
  } }
 }
}'''


MEDIA_HARNESS = HARNESS.replace('import qs.modules.components', 'import qs.modules.bar.island\nimport qs.modules.widgets.dashboard.widgets\nimport qs.modules.components').replace(
    'AudioMixerPanel { id:panel; x:24; y:24; width:parent.width-48; height:parent.height-48; currentSection:"equalizer" }',
    'IslandMediaCenterPanel { id:panel; x:24; y:24; width:parent.width-48; height:implicitHeight }\n'
    'FullPlayer { id:standard; visible:false; width:parent.width-48; height:implicitHeight }'
).replace(
    '    Config.theme.shellStyle="orbital"; tester.wait(40);',
    '    tester.verify(find(panel,"media-equalizer")!==null);\n'
    '    tester.verify(find(panel,"lyrics-viewport")===null);\n'
    '    tester.verify(find(standard,"media-equalizer")!==null);\n'
    '    tester.verify(find(standard,"lyrics-viewport")===null);\n'
    '    tester.verify(find(panel,"media-equalizer-scroll")===null);\n'
    '    for(const size of [14,20]) { Config.theme.fontSize=size;\n'
    '     for(const w of [420,620,900]) { panel.width=w; tester.wait(30);\n'
    '      const eq=find(panel,"media-equalizer");\n'
    '      for(let i=0;i<10;i++) { const slider=find(panel,"audio-eq-band-"+i);\n'
    '       tester.compare(slider.orientation,Qt.Vertical);\n'
    '       const pos=slider.mapToItem(eq,0,0); tester.verify(pos.x>=0 && pos.y>=0,"negative band "+i+" "+pos);\n'
    '       if(pos.x+slider.width>eq.width+1 || pos.y+slider.height>eq.height+1) console.error("OVERFLOW",i,w,size,pos,slider.width,slider.height,eq.width,eq.height); tester.verify(pos.x+slider.width<=eq.width+1 && pos.y+slider.height<=eq.height+1,"overflow band "+i+" width "+w+" size "+size+" pos "+pos+" eq "+eq.width+"x"+eq.height);\n'
    '      }\n'
    '     }\n'
    '    }\n'
    '    Config.theme.fontSize=14; panel.width=Math.min(620,previewSurface.width-48); tester.wait(40); tester.verify(panel.height+48<=720,"Media center must fit a 720p screen");\n'
    '    Config.theme.shellStyle="orbital"; tester.wait(40);'
)


class EqualizerUiTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
    def test_audio_tab(self):
        self.run_ui(HARNESS)

    def test_media_centers(self):
        self.run_ui(MEDIA_HARNESS)

    def run_ui(self, harness):
        with tempfile.TemporaryDirectory(prefix='enclosure-eq-ui-') as folder:
            root = Path(folder)
            for name in ('modules', 'config', 'assets'):
                shutil.copytree(APP/name, root/name)
            (root/'scripts').mkdir()
            for name in ('audio_equalizer.py', 'audio_eq_dsp.py'):
                shutil.copy2(APP/'scripts'/name, root/'scripts'/name)
            (root/'shell.qml').write_text(harness)
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
                self.assertEqual(saved['gains'][0],2.5)
                self.assertFalse(saved['enabled'])
            finally:
                worker.terminate()
                worker.communicate(timeout=5)


if __name__ == '__main__':
    unittest.main()
