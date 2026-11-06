"""GPU query failures must not stall or prevent the next monitor sample."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import mock_open, patch

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/system_monitor.py'
spec = importlib.util.spec_from_file_location('gpu_monitor', SOURCE)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class GpuMonitorTests(unittest.TestCase):
    def instance(self):
        instance = monitor.SystemMonitor.__new__(monitor.SystemMonitor)
        instance.gpu_info = [{'vendor': 'nvidia', 'pci_id': '0000:01:00.0'}]
        instance._get_pci_driver = lambda _: 'nvidia'
        return instance

    def test_timeout_returns_fallback_and_next_sample_recovers(self):
        instance = self.instance()
        with patch.object(monitor.os.path, 'exists', return_value=False), patch.object(
                monitor.subprocess, 'check_output', side_effect=[
                    subprocess.TimeoutExpired('nvidia-smi', 3), b'42, 60, 512, 2048, 1200']) as query:
            self.assertEqual(instance.get_gpu_stats(), ([0.0], [-1], ['nvidia'], [0], [0], [0.0]))
            self.assertEqual(instance.get_gpu_stats(),
                             ([42.0], [60], ['nvidia'], [512*1024**2], [2048*1024**2], [1200.0]))
            self.assertEqual(query.call_args.kwargs['timeout'], 3)

    def test_suspended_gpu_is_not_woken(self):
        with patch.object(monitor.os.path, 'exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='suspended\n')), \
             patch.object(monitor.subprocess, 'check_output') as query:
            self.assertEqual(self.instance().get_gpu_stats()[0], [0.0])
            query.assert_not_called()

    def test_stalled_pci_name_query_uses_vendor_fallback(self):
        with patch.object(monitor.subprocess, 'check_output',
                          side_effect=subprocess.TimeoutExpired('lspci', 3)) as query:
            self.assertEqual(self.instance()._detect_gpu_name('0000:01:00.0', 'amd'), 'AMD GPU')
            self.assertEqual(query.call_args.kwargs['timeout'], 3)

    def test_malformed_or_missing_query_returns_fallback(self):
        for response in (b'N/A, N/A, N/A, N/A, N/A', b'1, 2', FileNotFoundError('missing')):
            kwargs = {'side_effect': response} if isinstance(response, Exception) else {'return_value': response}
            with self.subTest(response=response), patch.object(monitor.os.path, 'exists', return_value=False), \
                 patch.object(monitor.subprocess, 'check_output', **kwargs):
                self.assertEqual(self.instance().get_gpu_stats()[1], [-1])
