import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('input_guard', Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/input_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class InputSafety(unittest.TestCase):
    def setUp(self):
        self.g = guard.Guard()
        self.found = {'keyboard': ['kbd'], 'touchscreen': ['touch']}
        self.open = patch.object(guard.os, 'open', return_value=7).start()
        self.close = patch.object(guard.os, 'close').start()
        self.ioctl = patch.object(guard.fcntl, 'ioctl').start()
        self.addCleanup(patch.stopall)

    def test_never_disable_both(self):
        self.g.toggle('keyboard', self.found)
        self.g.toggle('touchscreen', self.found)
        self.assertEqual(self.g.disabled, 'keyboard')
        self.assertEqual(self.ioctl.call_count, 1)
        self.g.toggle('keyboard', self.found)
        self.assertIsNone(self.g.disabled)
        self.close.assert_called_with(7)

    def test_fallback_required(self):
        self.g.toggle('keyboard', {'keyboard': ['kbd'], 'touchscreen': []})
        self.ioctl.assert_not_called()

    def test_disconnect_restores_but_no_timer(self):
        self.g.toggle('keyboard', self.found)
        self.g.state({'keyboard': ['kbd'], 'touchscreen': []})
        self.assertIsNone(self.g.disabled)
        self.g.toggle('touchscreen', self.found)
        for _ in range(1000):
            self.g.state(self.found)
        self.assertEqual(self.g.disabled, 'touchscreen')

    def test_combined_device_cannot_disable_fallback(self):
        self.g.toggle('keyboard', {'keyboard': ['shared'], 'touchscreen': ['shared']})
        self.ioctl.assert_not_called()

    def test_partial_grab_failure_rolls_back(self):
        self.ioctl.side_effect = PermissionError(13, 'Denied')
        self.g.toggle('keyboard', self.found)
        self.assertIsNone(self.g.disabled)
        self.assertFalse(self.g.handles)
        self.close.assert_called_with(7)


if __name__ == '__main__':
    unittest.main()
