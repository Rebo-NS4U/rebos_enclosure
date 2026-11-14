import importlib.util
import io
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageFont

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
                    self.assertEqual(image.size, (640, 340))
                return subprocess.CompletedProcess(args, 0, ' Text & <symbols>\n')
            region = dict(x=10, y=20, width=100, height=50, viewWidth=400, viewHeight=300)
            with patch.object(ocr.subprocess, 'run', side_effect=recognize):
                self.assertEqual(ocr.recognize(source, region)['text'], 'Text & <symbols>')
            self.assertFalse(crops[0].exists())

    def test_small_numbers_and_symbols_with_real_tesseract(self):
        font_path = Path('/usr/share/fonts/noto/NotoSansMono-Regular.ttf')
        if not shutil.which('tesseract') or not font_path.exists():
            self.skipTest('Requires Tesseract English data and Noto Sans Mono')
        font = ImageFont.truetype(str(font_path), 14)
        samples = ['0123456789 98.76% $123.45',
                   '(42 + 17) / 3; [a_b] {id: 907}',
                   'Code: AB-1234 / 2026-11-14']
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'screen.png'
            for background, foreground in [('white', 'black'), ('#202020', '#dddddd')]:
                for text in samples:
                    with self.subTest(background=background, text=text):
                        image = Image.new('RGB', (450, 28), background)
                        ImageDraw.Draw(image).text((3, 3), text, font=font, fill=foreground)
                        image.save(source)
                        region = dict(x=0, y=0, width=450, height=28, viewWidth=450, viewHeight=28)
                        self.assertEqual(ocr.recognize(source, region)['text'], text)

    def test_preprocessing_normalizes_polarity_and_bounds_size(self):
        for background in ['white', 'black']:
            prepared = ocr.prepare_text(Image.new('RGB', (20, 10), background))
            self.assertEqual(prepared.size, (100, 70))
            self.assertEqual(prepared.getpixel((25, 25)), 255)
        self.assertEqual(ocr.prepare_text(Image.new('L', (3000, 10), 255)).width, 6040)

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
