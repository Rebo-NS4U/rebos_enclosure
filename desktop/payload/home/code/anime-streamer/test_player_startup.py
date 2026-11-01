import subprocess
import unittest
from unittest.mock import patch
import vlc_session


class PluginDetectionTests(unittest.TestCase):
    def test_available_options(self):
        with patch.object(vlc_session.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '--pause-click-mouse-button')):
            self.assertTrue(vlc_session.pause_click_available())

    def test_missing_plugin(self):
        with patch.object(vlc_session.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'No matching module found')):
            self.assertFalse(vlc_session.pause_click_available())

    def test_failed_probe(self):
        for error in (OSError('missing executable'), subprocess.TimeoutExpired('vlc', 5)):
            with self.subTest(error=error), patch.object(vlc_session.subprocess, 'run', side_effect=error):
                self.assertFalse(vlc_session.pause_click_available())


if __name__ == '__main__':
    unittest.main()
