"""Verify driver transitions without changing hardware."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, call
import subprocess
import thinkpad_fan as fan


class FanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.control = Path(self.temp.name) / 'control'
        self.proc = Path(self.temp.name) / 'fan'
        self.control.write_text('Y\n')
        self.proc.write_text('status: disabled\nspeed: 0\nlevel: 0\n')
        self.paths = patch.multiple(fan, CONTROL=self.control, FAN=self.proc)
        self.paths.start()
        self.addCleanup(self.paths.stop)

    def test_live_readings(self):
        self.assertEqual(fan.status(), {'status': 'disabled', 'speed': '0', 'level': '0'})

    def test_off_and_automatic_write_proc_commands(self):
        with patch.object(fan.subprocess, 'run') as run, patch.object(fan, 'status', side_effect=[{'level': '0'}, {'level': 'auto'}]):
            fan.apply('off')
            self.assertEqual(self.proc.read_text(), 'level 0\n')
            fan.apply('auto')
            self.assertEqual(self.proc.read_text(), 'level auto\n')
            run.assert_not_called()

    def test_disabled_control_reloads_driver_before_stop(self):
        self.control.write_text('N\n')
        with patch.object(fan.subprocess, 'run') as run, patch.object(fan, 'status', return_value={'level': '0'}):
            fan.apply('off')
        self.assertEqual(run.call_args_list, [call(['modprobe', '-r', 'thinkpad_acpi'], check=True), call(['modprobe', 'thinkpad_acpi', 'fan_control=1'], check=True)])
        self.assertEqual(self.proc.read_text(), 'level 0\n')

    def test_load_failure_restores_driver_and_does_not_write(self):
        self.control.write_text('N\n')
        before = self.proc.read_text()
        with patch.object(fan.subprocess, 'run', side_effect=[None, subprocess.CalledProcessError(1, 'modprobe'), None]) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                fan.apply('off')
        self.assertEqual(run.call_args_list[-1], call(['modprobe', 'thinkpad_acpi'], check=False))
        self.assertEqual(self.proc.read_text(), before)

    def test_busy_driver_does_not_write(self):
        self.control.write_text('N\n')
        before = self.proc.read_text()
        with patch.object(fan.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'modprobe')):
            with self.assertRaises(subprocess.CalledProcessError):
                fan.apply('off')
        self.assertEqual(self.proc.read_text(), before)

    def test_rejects_unknown_mode(self):
        with self.assertRaises(ValueError):
            fan.apply('invalid')


if __name__ == '__main__':
    unittest.main()
