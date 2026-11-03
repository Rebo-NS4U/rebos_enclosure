import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class DevelopmentLauncherTests(unittest.TestCase):
    def test_home_checkout_is_discovered_without_source_links(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            checkout = home / 'rebos_enclosure'
            checkout.mkdir()
            (checkout / '.git').mkdir()
            (checkout / 'dev.sh').touch()
            with patch.dict(os.environ, {}, clear=True), patch('pathlib.Path.home', return_value=home), patch('subprocess.run') as run, patch('os.execv', side_effect=RuntimeError('launched')) as execute:
                run.return_value.returncode = 0
                run.return_value.stdout = 'https://github.com/Rebo-NS4U/rebos_enclosure.git\n'
                with self.assertRaisesRegex(RuntimeError, 'launched'):
                    runpy.run_path(str(ROOT / 'system/bin/enclosure-dev'), run_name='__main__')
                self.assertEqual(execute.call_args.args[1][1], str(checkout / 'dev.sh'))
