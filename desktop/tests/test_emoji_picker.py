"""Exercise emoji selection without opening a menu or touching the clipboard."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2] / 'system/bin/emoji-dmenu'


class EmojiPickerTests(unittest.TestCase):
    def run_picker(self, selection='😀 grinning face', status='0'):
        with tempfile.TemporaryDirectory(prefix='emoji picker ') as folder:
            root = Path(folder)
            script = root / 'emoji picker'
            script.write_bytes(SOURCE.read_bytes())
            tools = root / 'bin'
            tools.mkdir()
            for name, text in {
                'fuzzel': '#!/bin/sh\ncat > "$SCAN_INPUT"\nprintf "%s\\n" "$SCAN_SELECTION"\nexit "$SCAN_STATUS"\n',
                'wl-copy': '#!/bin/sh\ncat > "$SCAN_CLIPBOARD"\n',
            }.items():
                p = tools / name
                p.write_text(text)
                p.chmod(0o700)
            env = dict(os.environ, PATH=str(tools)+':'+os.environ['PATH'],
                       SCAN_INPUT=str(root/'input'), SCAN_SELECTION=selection,
                       SCAN_STATUS=status, SCAN_CLIPBOARD=str(root/'clipboard'))
            result = subprocess.run(['bash', str(script)], env=env, capture_output=True, timeout=5)
            clip = root / 'clipboard'
            return result, clip.read_bytes() if clip.exists() else None, (root/'input').read_text()

    def test_path_with_spaces_copies_only_selected_emoji(self):
        result, clipboard, catalog = self.run_picker()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(clipboard, '😀'.encode())
        self.assertIn('😀 grinning face', catalog)
        self.assertIn('¯\\_(ツ)_/¯ shrug', catalog)

    def test_multi_codepoint_emoji_stays_intact(self):
        result, clipboard, _ = self.run_picker('👉👈 etou ughhhhhhh shy')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(clipboard, '👉👈'.encode())

    def test_cancellation_preserves_clipboard(self):
        result, clipboard, _ = self.run_picker(status='1')
        self.assertEqual(result.returncode, 1)
        self.assertIsNone(clipboard)

    def test_empty_selection_preserves_clipboard(self):
        result, clipboard, _ = self.run_picker(selection='')
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(clipboard)
