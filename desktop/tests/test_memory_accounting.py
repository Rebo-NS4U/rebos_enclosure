"""Memory samples reconcile without double-counting shared resident pages."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/process_monitor.py'
spec = importlib.util.spec_from_file_location('memory_monitor', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MemoryAccountingTests(unittest.TestCase):
    def test_proportional_memory_and_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            self.assertEqual(module.ProcessMonitor.proportional_memory(base), (0, False))
            (base / 'smaps_rollup').write_text('Rss: 800 kB\nPss: 125 kB\n')
            self.assertEqual(module.ProcessMonitor.proportional_memory(base), (125 * 1024, True))

    def test_reconciles_positive_and_negative_adjustments(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            (proc / '10').mkdir()
            (proc / 'meminfo').write_text('MemTotal: 1000 kB\nMemAvailable: 400 kB\n')
            for memory, readable in [(200 * 1024, True), (800 * 1024, True), (0, False)]:
                row = dict(pid=10, ppid=1, name='test', start=1, ticks=0,
                           ram=memory, memory_available=readable, sockets=0, io_available=False,
                           read=0, write=0, gpu={})
                monitor = module.ProcessMonitor(proc)
                with patch.object(monitor, 'snapshot', return_value=row), \
                     patch.object(monitor, 'proportional_memory', return_value=(memory, readable)):
                    sample = monitor.sample(memory_accounting=True)
                stats = sample['memory']
                self.assertEqual(stats['attributed'] + stats['other'], stats['used'])
                self.assertEqual(stats['used'] + stats['available'], stats['total'])
                self.assertEqual(stats['unreadable'], int(not readable))
                self.assertEqual(sum(p['ram'] for p in sample['processes']), stats['attributed'])
