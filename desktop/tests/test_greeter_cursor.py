"""Exercise wlroots' real cursor fallback without starting a display server."""
import ctypes as C
import ctypes.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class Image(C.Structure):
    _fields_ = [(name, C.c_uint32) for name in
                ('width', 'height', 'hotspot_x', 'hotspot_y', 'delay')] + [('buffer', C.c_void_p)]


class Cursor(C.Structure):
    _fields_ = [('count', C.c_uint), ('images', C.POINTER(C.POINTER(Image)))]


class GreeterCursorTests(unittest.TestCase):
    def test_unnamed_and_default_requests_use_googledot(self):
        library = next((path for name in ('wlroots-0.20', 'wlroots-0.19', 'wlroots-0.18', 'wlroots')
                        if (path := ctypes.util.find_library(name))), None)
        if not library:
            self.skipTest('wlroots is not installed')
        lib = C.CDLL(library)
        lib.wlr_xcursor_theme_load.argtypes = [C.c_char_p, C.c_int]
        lib.wlr_xcursor_theme_load.restype = C.c_void_p
        lib.wlr_xcursor_theme_get_cursor.argtypes = [C.c_void_p, C.c_char_p]
        lib.wlr_xcursor_theme_get_cursor.restype = C.POINTER(Cursor)
        lib.wlr_xcursor_theme_destroy.argtypes = [C.c_void_p]
        # Use the shipped icons, not a possibly different host installation.
        search = ':'.join(str(p) for p in (ROOT / 'system/etc/rebos-greeter/icons',
                                          ROOT / 'system/share/icons'))
        def pixels(theme):
            handle = lib.wlr_xcursor_theme_load(theme, 20)
            self.assertTrue(handle)
            try:
                cursor = lib.wlr_xcursor_theme_get_cursor(handle, b'left_ptr')
                self.assertTrue(cursor)
                image = cursor.contents.images[0].contents
                return image.width, image.height, C.string_at(image.buffer, image.width * image.height * 4)
            finally:
                lib.wlr_xcursor_theme_destroy(handle)
        with patch.dict(os.environ, {'XCURSOR_PATH': search, 'HOME': '/nonexistent'}):
            expected = pixels(b'GoogleDot-Black')
            self.assertEqual(pixels(None), expected)
            self.assertEqual(pixels(b'default'), expected)


if __name__ == '__main__':
    unittest.main()
