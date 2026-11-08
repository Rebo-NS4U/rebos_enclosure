"""Prevent controls from silently falling back to the desktop's native Qt style."""
from pathlib import Path
import re
import unittest

SHELL = Path(__file__).resolve().parents[2] / 'system/apps/shell'

class ControlStyleTests(unittest.TestCase):
    def test_shell_controls_own_their_surfaces_and_labels(self):
        missing = []
        for path in SHELL.rglob('*.qml'):
            source = path.read_text()
            for match in re.finditer(r'\b(Button|ToolButton|RoundButton|Slider)\s*\{', source):
                depth, end = 1, match.end()
                while depth and end < len(source):
                    depth += (source[end] == '{') - (source[end] == '}')
                    end += 1
                body = source[match.end():end]
                required = ('background:', 'handle:') if match[1] == 'Slider' else ('background:', 'contentItem:')
                for property in required:
                    if property not in body:
                        missing.append(f'{path.relative_to(SHELL)}:{source.count(chr(10), 0, match.start()) + 1} missing {property}')
        self.assertEqual(missing, [], '\n'.join(missing))

if __name__ == '__main__': unittest.main()
