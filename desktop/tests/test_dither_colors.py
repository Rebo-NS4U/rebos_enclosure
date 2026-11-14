"""Verify ordered wallpaper dithering preserves color and source pixels."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('dither', ROOT / 'system/apps/shell/scripts/dither_wallpaper.py')
dither = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dither)

class DitherColorsTests(unittest.TestCase):
    def test_colors_texture_and_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source.png'
            color = (73, 139, 201)
            Image.new('RGB', (64, 64), color).save(source)
            original = source.read_bytes()
            outputs = []
            contrasts = []
            for strength in dither.STRENGTHS:
                output = dither.convert(source, root / 'cache', strength=strength)
                self.assertEqual(output, dither.convert(source, root / 'cache', strength=strength))
                with Image.open(output) as result:
                    self.assertEqual(result.size, (64, 64))
                    self.assertGreater(len(result.getcolors()), 1)
                    for actual, expected in zip(ImageStat.Stat(result).mean, color):
                        self.assertLess(abs(actual - expected), 3)
                    contrasts.append(sum(ImageStat.Stat(result).var))
                    outputs.append(result.tobytes())
            self.assertEqual(len(set(outputs)), 3)
            self.assertLess(contrasts[0], contrasts[1])
            self.assertLess(contrasts[1], contrasts[2])
            self.assertEqual(source.read_bytes(), original)
