import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

path = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/desktop_blur.py'
spec = importlib.util.spec_from_file_location('desktop_blur', path)
blur = importlib.util.module_from_spec(spec)
spec.loader.exec_module(blur)

class BlurTests(unittest.TestCase):
    def test_strength_and_scope(self):
        for mode in blur.MODES:
            offsets = []
            for strength in (0, 50, 100):
                text = blur.render(mode, strength)
                offsets.append(float(re.search(r'offset ([\d.]+)', text)[1]))
                with tempfile.NamedTemporaryFile(suffix='.kdl', mode='w') as f:
                    f.write(text)
                    f.flush()
                    result = subprocess.run(['niri', 'validate', '-c', f.name], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(offsets, sorted(set(offsets)))
        self.assertIn('exclude namespace=', blur.render('shell'))
        self.assertNotIn('exclude namespace=', blur.render('off'))
        for value in (-1, 101):
            with self.assertRaises(ValueError): blur.render('medium', value)

if __name__ == '__main__': unittest.main()
