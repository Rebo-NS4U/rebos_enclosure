"""Check wallpaper categories and cache migration using synthetic images."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'system/apps/shell/scripts/wallpaper_color_index.py'
spec = importlib.util.spec_from_file_location('wallpaper_color_index', SCRIPT)
indexer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(indexer)


class WallpaperColorIndexTests(unittest.TestCase):
    def test_neutral_background_beats_color_accent(self):
        for background, expected in [('#808080', 'gray'), ('#ffffff', 'white'), ('#101010', 'black')]:
            with self.subTest(expected=expected):
                image = Image.new('RGB', (100, 100), background)
                image.paste('#ff0000', (0, 0, 30, 100))
                self.assertEqual(indexer.color_info(image)['group'], expected)

    def test_dominant_color_beats_neutral_accent(self):
        image = Image.new('RGB', (100, 100), '#2455dd')
        image.paste('#808080', (0, 0, 30, 100))
        self.assertEqual(indexer.color_info(image)['group'], 'blue')

    def test_muted_dark_noise_is_neutral(self):
        self.assertEqual(indexer.color_info(Image.new('RGB', (20, 20), (50, 40, 40)))['group'], 'gray')

    def test_purple_and_pink(self):
        for color, group in [('#aa22cc', 'purple'), ('#ee4488', 'pink')]:
            self.assertEqual(indexer.color_info(Image.new('RGB', (20, 20), color))['group'], group)

    def test_brightness_and_source_preserved(self):
        image = Image.new('RGB', (200, 100), 'white')
        self.assertEqual(indexer.color_info(image)['brightness'], 1)
        self.assertEqual(image.size, (200, 100))
        self.assertEqual(indexer.color_info(Image.new('RGB', (20, 20), 'black'))['brightness'], 0)

    def test_cache_migration_transparency_and_reuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'walls'
            root.mkdir()
            cache = Path(temporary) / 'cache'
            cache.mkdir()
            path = root / 'transparent.png'
            Image.new('RGBA', (100, 100), (255, 0, 0, 0)).save(path)
            cache_file = cache / 'wallpaper-color-index.json'
            cache_file.write_text(json.dumps({'version': 2, 'entries': {str(path): {'group': 'red'}}}))
            result = indexer.build_index(root, cache)
            self.assertEqual(result[str(path)]['group'], 'black')
            self.assertEqual(json.loads(cache_file.read_text())['version'], indexer.CACHE_VERSION)
            self.assertEqual(indexer.build_index(root, cache), result)


if __name__ == '__main__':
    unittest.main()
