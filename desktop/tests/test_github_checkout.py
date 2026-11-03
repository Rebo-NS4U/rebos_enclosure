"""Copied desktop installs resolve only verified official checkouts."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts'
sys.path.insert(0, str(SCRIPTS))
import github_projects as projects


class DiscoveryTests(unittest.TestCase):
    def test_copied_install(self):
        home = Path('/example')
        target = home / 'rebos_enclosure'
        def checkout(path):
            if Path(path) == target:
                return target, 'Rebo-NS4U/rebos_enclosure'
            raise ValueError('Missing')
        with patch.object(projects.status, 'linked_checkout', return_value=None), patch.object(projects, 'checkout', side_effect=checkout):
            self.assertEqual(projects.desktop_checkout(home), target)

    def test_wrong_remote_is_rejected(self):
        with patch.object(projects.status, 'linked_checkout', return_value=None), patch.object(projects, 'checkout', return_value=(Path('/other'), 'other/project')):
            self.assertIsNone(projects.desktop_checkout(Path('/example')))

    def test_linked_install_keeps_priority(self):
        with patch.object(projects.status, 'linked_checkout', return_value=Path('/linked')):
            self.assertEqual(projects.desktop_checkout(Path('/example')), Path('/linked'))

    def test_expand_control_stays_enabled(self):
        controls = SCRIPTS.parent / 'modules/widgets/dashboard/controls'
        section = (controls / 'GithubSection.qml').read_text()
        self.assertIn('enabled: root.actionsEnabled', section)
        self.assertNotIn('enabled: root.actionsEnabled', section.split('ColumnLayout { id: body')[0])
        self.assertIn('actionsEnabled: root.canEdit', (controls / 'GithubProjects.qml').read_text())

if __name__ == '__main__':
    unittest.main()
