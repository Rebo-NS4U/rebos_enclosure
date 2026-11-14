import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/screen_text.py'
spec = importlib.util.spec_from_file_location('screen_text', SCRIPT)
ocr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ocr)


class ScreenTextTest(unittest.TestCase):
    def test_scaled_region_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'screen.png'
            Image.new('RGB', (800, 600), 'white').save(source)
            crops = []
            def recognize(args, **kwargs):
                crops.append(Path(args[1]))
                with Image.open(crops[-1]) as image:
                    self.assertEqual(image.size, (200, 100))
                return subprocess.CompletedProcess(args, 0, ' Text & <symbols>\n')
            region = dict(x=10, y=20, width=100, height=50, viewWidth=400, viewHeight=300)
            with patch.object(ocr.subprocess, 'run', side_effect=recognize):
                self.assertEqual(ocr.recognize(source, region)['text'], 'Text & <symbols>')
            self.assertFalse(crops[0].exists())

    def test_rejects_invalid_regions(self):
        for width in [0, -10, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                ocr.recognize('unused',dict(x=0,y=0,width=width,height=20,viewWidth=100,viewHeight=100))

    def test_recognition_failure_cleans_crop(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'screen.png'
            Image.new('RGB',(100,100)).save(source)
            crops=[]
            def fail(args, **kwargs):
                crops.append(Path(args[1]))
                raise subprocess.CalledProcessError(1,args)
            with patch.object(ocr.subprocess,'run',side_effect=fail):
                with self.assertRaises(subprocess.CalledProcessError):
                    ocr.recognize(source,dict(x=0,y=0,width=20,height=20,viewWidth=100,viewHeight=100))
            self.assertFalse(crops[0].exists())

    def test_session_eof_deletes_screen_captures(self):
        outputs='{"DP-1":{"logical":{"width":800,"height":600}},"off":{"logical":null}}'
        paths=[]
        def capture(args,**kwargs):
            paths.append(Path(args[-1]))
            Image.new('RGB',(800,600)).save(paths[-1])
        with patch.object(ocr.subprocess,'check_output',return_value=outputs), \
             patch.object(ocr.subprocess,'run',side_effect=capture), \
             patch.object(ocr.signal,'signal'),patch.object(ocr.sys,'stdin',io.StringIO('')), \
             patch.object(ocr,'emit') as emit:
            ocr.session()
            self.assertEqual(set(emit.call_args.args[0]['screens']),{'DP-1'})
        self.assertFalse(paths[0].parent.exists())

    def test_capture_failure_deletes_session(self):
        paths=[]
        def fail(args,**kwargs):
            paths.append(Path(args[-1]))
            raise subprocess.CalledProcessError(1,args)
        with patch.object(ocr.subprocess,'check_output',return_value='{"DP-1":{"logical":{ "width":800}}}'), \
             patch.object(ocr.subprocess,'run',side_effect=fail),patch.object(ocr.signal,'signal'):
            with self.assertRaises(subprocess.CalledProcessError):ocr.session()
        self.assertFalse(paths[0].parent.exists())
