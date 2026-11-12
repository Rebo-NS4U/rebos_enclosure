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
