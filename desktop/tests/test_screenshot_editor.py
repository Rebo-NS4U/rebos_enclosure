"""Verify native-resolution export, redaction and private capture cleanup."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('screenshot_editor', ROOT / 'system/apps/shell/scripts/screenshot_editor.py')
editor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(editor)


class ScreenshotExportTest(unittest.TestCase):
    def spec(self, operations=None):
        return dict(width=100, height=50, crop=dict(x=10,y=5,width=60,height=30), operations=operations or [])

    def test_scaled_crop_and_opaque_redaction(self):
        image = Image.new('RGB', (200,100), 'white')
        op = dict(tool='redact', points=[dict(x=20,y=10),dict(x=30,y=20)])
        result = editor.render(image, self.spec([op]))
        self.assertEqual(result.size, (120,60))
        self.assertEqual(result.getpixel((25,15)), (0,0,0))
        self.assertEqual(result.getpixel((5,5)), (255,255,255))

    def test_reverse_drag_shapes_and_drawing(self):
        image = Image.new('RGB', (200,100), 'white')
        for tool in ['arrow','rectangle','redact','pen','text']:
            with self.subTest(tool=tool):
                op = dict(tool=tool, color='#ff0000', size=4, text='Hi', points=[dict(x=30,y=20),dict(x=20,y=10)])
                result = editor.render(image, self.spec([op]))
                self.assertNotEqual(result.tobytes(), image.crop((20,10,140,70)).tobytes())

    def test_empty_crop_rejected(self):
        spec = self.spec(); spec['crop']['width'] = 0
        with self.assertRaises(ValueError):
            editor.render(Image.new('RGB',(200,100)), spec)

    def test_capture_failure_removes_private_session(self):
        with tempfile.TemporaryDirectory() as runtime, patch.dict(os.environ, XDG_RUNTIME_DIR=runtime):
            with patch.object(editor.subprocess, 'check_output', side_effect=RuntimeError('No output')):
                with self.assertRaises(RuntimeError): editor.capture('area')
            self.assertEqual(list((Path(runtime)/'enclosure-screenshots').iterdir()), [])

    def test_save_and_copy_exports(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, HOME=directory):
            source = Path(directory)/'source.png'
            Image.new('RGB',(200,100),'white').save(source)
            import json
            args = ['editor','export',str(source),json.dumps(self.spec()),'save']
            with patch.object(editor.sys, 'argv', args), contextlib.redirect_stdout(io.StringIO()):
                editor.main()
            files = list((Path(directory)/'Pictures/Screenshots').glob('*.png'))
            self.assertEqual(len(files), 1)
            with Image.open(files[0]) as image: self.assertEqual(image.size, (120,60))
            args[-1] = 'copy'
            with patch.object(editor.sys, 'argv', args), patch.object(editor.subprocess, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
                editor.main()
                self.assertEqual(run.call_args.args[0], ['wl-copy','--type','image/png'])

    def test_launcher_modes(self):
        script = (ROOT/'system/bin/wayland-screenshot').read_text()
        self.assertIn('screenshot.qml', script)
        self.assertNotIn('satty', script)
        self.assertIn('area|edit|screen|output|window)', script)


class ScreenshotLauncherTest(unittest.TestCase):
    def test_warm_capture_uses_ipc_and_cold_capture_starts_once(self):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            qs = folder/'qs'
            qs.write_text("""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$TEST_LOG"
if [[ "$1" == -d ]]; then touch "$TEST_READY"; exit 0; fi
[[ -f "$TEST_READY" ]]
""")
            qs.chmod(0o755)
            env = {**os.environ, 'PATH':str(folder)+':'+os.environ['PATH'],
                   'HOME':directory, 'TEST_LOG':str(folder/'calls'), 'TEST_READY':str(folder/'ready')}
            launcher = ROOT/'system/bin/wayland-screenshot'
            subprocess.run(['bash',str(launcher),'screen'],env=env,check=True)
            calls = (folder/'calls').read_text().splitlines()
            self.assertEqual(sum(call.startswith('-d -n') for call in calls),1)
            self.assertTrue(calls[-1].endswith('call screenshot capture screen'))
            (folder/'calls').write_text('')
            subprocess.run(['bash',str(launcher),'area'],env=env,check=True)
            calls = (folder/'calls').read_text().splitlines()
            self.assertEqual(len(calls),1)
            self.assertTrue(calls[0].endswith('call screenshot capture area'))
            (folder/'calls').write_text('')
            subprocess.run(['bash',str(launcher),'--warm'],env=env,check=True)
            self.assertTrue((folder/'calls').read_text().startswith('-d -n'))



class ScreenshotQmlTest(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("ENCLOSURE_SCREENSHOT_UI_TEST") == "1", "Requires an explicitly selected Wayland test session")
    def test_overlay_edit_and_export_contract(self):
        import shutil
        import subprocess
        if not shutil.which('qs'):
            self.skipTest('Quickshell not installed')
        app = ROOT/'system/apps/shell'
        with tempfile.TemporaryDirectory(prefix='screenshot-qml-') as directory:
            folder = Path(directory)
            for name in ['modules','config','scripts','assets']:
                (folder/name).symlink_to(app/name, target_is_directory=True)
            Image.new('RGB',(1600,1000),'white').save(folder/'source.png')
            (folder/'shell.qml').write_text('''import QtQuick
import Quickshell
import qs.modules.screenshot
ShellRoot {
 QtObject {
  id: mockController
  property string imagePath: "SOURCE"
  property string mode: "screen"
  property string error: ""
  property var exported: null
  function close() {}
  function exportImage(spec, action) { exported = spec; }
 }
 ScreenshotOverlay { id: overlay; controller: mockController; visible: true }
 Timer { interval: 700; running: true; onTriggered: {
  try {
   function check(value, message) { if (!value) throw Error(message); }
   check(overlay.crop.width > 0, 'Screen mode automatically selects full image');
   overlay.fullImage();
   overlay.commit({tool:'redact', points:[{x:10,y:10},{x:20,y:20}]});
   check(overlay.operations.length === 1, 'Commit');
   overlay.undo(); check(overlay.operations.length === 0, 'Undo');
   overlay.redo(); check(overlay.operations.length === 1, 'Redo');
   overlay.exportImage('copy');
   check(mockController.exported && mockController.exported.width > 0, 'Export dimensions');
   check(mockController.exported.crop.width === mockController.exported.width, 'Full image crop');
   console.log('SCREENSHOT_QML_PASS');
  } catch (error) { console.log('SCREENSHOT_QML_FAIL ' + error); }
  Qt.quit();
 } }
}
'''.replace('SOURCE', str(folder/'source.png')))
            env = {**os.environ, 'QT_QPA_PLATFORM':'wayland', 'QS_DISABLE_FILE_WATCHER':'1'}
            result = subprocess.run(['qs','-p',str(folder/'shell.qml')], env=env, capture_output=True, text=True, timeout=15)
            output = result.stdout + result.stderr
            self.assertIn('SCREENSHOT_QML_PASS', output)
            self.assertNotIn('TypeError:', output)
            self.assertNotIn('ReferenceError:', output)

    @unittest.skipUnless(os.environ.get('ENCLOSURE_SCREENSHOT_UI_TEST') == '1', 'Requires an explicitly selected Wayland test session')
    def test_resident_reopen_pixels_and_pointer_selection(self):
        import json
        import subprocess
        app = ROOT/'system/apps/shell'
        with tempfile.TemporaryDirectory(prefix='screenshot-reopen-') as directory:
            folder = Path(directory)
            for name in ['modules','config','scripts','assets','version']:
                (folder/name).symlink_to(app/name)
            Image.new('RGB',(1600,1000),(0,240,0)).save(folder/'source.png')
            (folder/'capture.py').write_text("""import json, os, sys
if sys.argv[1] == 'capture':
    print(json.dumps({'path':os.environ['TEST_SOURCE'], 'screen':os.environ['TEST_SCREEN']}))
""")
            (folder/'shell.qml').write_text('''import QtQuick
import QtTest
import Quickshell
import qs.modules.screenshot
ShellRoot {
 id: harness
 property int cycle: 0
 Timer { interval: 4000; running: true; onTriggered: { console.log("REOPEN_FAIL Watchdog"); Qt.quit(); } }
 ScreenshotController { id: controller; helper: "HELPER" }
 TestCase { id: input; name: "ScreenshotPointer"; when: false }
 Component.onCompleted: controller.capture('area')
 Timer { id: waitForFrame; interval: 350; running: true; onTriggered: {
  try {
   const overlay = controller.overlay;
   if (!overlay) throw Error('Capture surface not created');
   if (!overlay.mask.item || overlay.mask.item.width !== overlay.width) throw Error('Input region must cover the screen');
   input.mousePress(overlay.contentItem, 200, 200, Qt.LeftButton);
   input.mouseMove(overlay.contentItem, 300, 300);
   input.mouseRelease(overlay.contentItem, 300, 300, Qt.LeftButton);
   if (overlay.crop.width < 95 || overlay.crop.height < 95) throw Error('Pointer selection not received');
   overlay.fullImage(); overlay.repaint();
   frameGrab.restart();
  } catch(error) { console.log('REOPEN_FAIL '+error); Qt.quit(); }
 } }
 // Wait for the 480 ms glass morph before checking settled screenshot pixels.
 Timer { id: frameGrab; interval: 600; onTriggered: {
  const overlay = controller.overlay;
  overlay.mask.item.grabToImage(result => {
   result.saveToFile('FOLDER/frame'+harness.cycle+'.png');
   controller.close();
   harness.cycle++;
   if (controller.overlay) { console.log('REOPEN_FAIL Surface not released'); Qt.quit(); return; }
   if (harness.cycle === 3) { console.log('REOPEN_PASS'); Qt.quit(); }
   else nextCapture.restart();
  });
 } }
 Timer { id: nextCapture; interval: 100; onTriggered: { controller.capture('area'); waitForFrame.restart(); } }
}
'''.replace('HELPER',str(folder/'capture.py')).replace('FOLDER',str(folder)))
            screen=json.loads(subprocess.check_output(['niri','msg','-j','focused-output']))['name']
            env={**os.environ,'QT_QPA_PLATFORM':'wayland','QS_DISABLE_FILE_WATCHER':'1',
                 'TEST_SOURCE':str(folder/'source.png'),'TEST_SCREEN':screen}
            result=subprocess.run(['qs','-p',str(folder/'shell.qml')],env=env,capture_output=True,text=True,timeout=15)
            output=result.stdout+result.stderr
            self.assertIn('REOPEN_PASS',output)
            for index in range(3):
                with Image.open(folder/f'frame{index}.png') as image:
                    pixel=image.getpixel((image.width//2,image.height//2))
                    self.assertGreater(pixel[1],200, f'Black screenshot after reopen {index}: {pixel}')
