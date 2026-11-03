"""Exercise new-source deployment, personal settings, updates and exact recovery."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import deploy
import organize
from layout import inventory, source


class StorageLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'checkout'
        self.payload = self.root / 'desktop/payload'
        self.payload.mkdir(parents=True)
        self.home = Path(self.tmp.name) / 'home'
        self.home.mkdir()
        files = {'config/kitty/kitty.conf': 'default\n',
                 'system/apps/shell/shell.qml': 'old code\n',
                 'system/bin/example': '#!/bin/sh\ntrue\n'}
        for name, content in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        data = {'layout': 2, 'units': ['.config/kitty', '.config/quickshell', '.local/bin/example'],
                'sources': {'.config/kitty': {'source': 'config/kitty', 'kind': 'personal'},
                            '.config/quickshell': {'source': 'system/apps/shell', 'kind': 'managed'},
                            '.local/bin/example': {'source': 'system/bin/example', 'kind': 'managed'}}}
        (self.payload / 'manifest.json').write_text(json.dumps(data))
        self.rehash()

    def rehash(self):
        hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in inventory(self.payload).items()}
        (self.payload / 'checksums.json').write_text(json.dumps(hashes))

    def test_preview_leaves_home_empty_and_checks_new_source(self):
        deploy.install(self.payload, self.home, dry_run=True)
        self.assertEqual(list(self.home.iterdir()), [])
        source(self.payload, '.config/quickshell/shell.qml').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            deploy.install(self.payload, self.home)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_revision_record_tracks_config_and_system_edits_outside_metadata(self):
        def git(*args):
            return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
        git('init', '-b', 'main')
        git('remote', 'add', 'origin', 'https://github.com/Rebo-NS4U/rebos_enclosure.git')
        git('add', 'config', 'system', 'desktop/payload')
        git('-c', 'user.name=Layout Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture')
        self.assertFalse(deploy.source_record(self.payload)['dirty'])
        (self.root / 'config/kitty/kitty.conf').write_text('changed default\n')
        self.assertTrue(deploy.source_record(self.payload)['dirty'])
        (self.root / 'config/kitty/kitty.conf').write_text('default\n')
        (self.root / 'system/apps/shell/shell.qml').write_text('changed source\n')
        self.assertTrue(deploy.source_record(self.payload)['dirty'])

    def test_fresh_install_has_separate_personal_defaults_and_system_storage(self):
        backup = deploy.install(self.payload, self.home)
        personal = self.home / '.config/enclosure/kitty/kitty.conf'
        system = self.home / '.local/share/enclosure/system/apps/shell/shell.qml'
        self.assertTrue((self.home / '.config/kitty').is_symlink())
        self.assertTrue((self.home / '.config/quickshell').is_symlink())
        self.assertEqual(personal.read_text(), 'default\n')
        self.assertEqual(system.read_text(), 'old code\n')
        self.assertEqual((self.home / '.local/share/enclosure/defaults/kitty/kitty.conf').read_text(), 'default\n')
        self.assertEqual(organize.plan(self.home, self.payload), [])
        deploy.restore(backup)
        self.assertFalse((self.home / '.config/kitty').exists())
        self.assertFalse(system.exists())
        self.assertFalse(personal.exists())

    def test_update_refreshes_system_and_unchanged_defaults_but_keeps_personal_edit(self):
        deploy.install(self.payload, self.home, preserve_preferences=True)
        personal = self.home / '.config/enclosure/kitty/kitty.conf'
        personal.write_text('my settings\n')
        (self.root / 'config/kitty/kitty.conf').write_text('new default\n')
        (self.root / 'system/apps/shell/shell.qml').write_text('new code\n')
        self.rehash()
        backup = deploy.install(self.payload, self.home, preserve_preferences=True)
        self.assertEqual(personal.read_text(), 'my settings\n')
        self.assertEqual((self.home / '.config/quickshell/shell.qml').read_text(), 'new code\n')
        self.assertEqual((self.home / '.local/share/enclosure/defaults/kitty/kitty.conf').read_text(), 'new default\n')
        deploy.restore(backup)
        self.assertEqual(personal.read_text(), 'my settings\n')
        self.assertEqual((self.home / '.config/quickshell/shell.qml').read_text(), 'old code\n')

    def test_update_unchanged_personal_file_and_add_new_defaults_through_alias(self):
        deploy.install(self.payload, self.home, preserve_preferences=True)
        (self.root / 'config/kitty/kitty.conf').write_text('updated\n')
        (self.root / 'config/kitty/new.conf').write_text('new option\n')
        self.rehash()
        backup = deploy.install(self.payload, self.home, preserve_preferences=True)
        self.assertTrue((self.home / '.config/kitty').is_symlink())
        self.assertEqual((self.home / '.config/kitty/kitty.conf').read_text(), 'updated\n')
        self.assertEqual((self.home / '.config/kitty/new.conf').read_text(), 'new option\n')
        deploy.restore(backup)
        self.assertEqual((self.home / '.config/kitty/kitty.conf').read_text(), 'default\n')
        self.assertFalse((self.home / '.config/kitty/new.conf').exists())

    def test_existing_configuration_moves_without_losing_unknown_personal_files(self):
        old = self.home / '.config/kitty'
        old.mkdir(parents=True)
        (old / 'kitty.conf').write_text('custom\n')
        (old / 'local.conf').write_text('private local settings\n')
        inode = (old / 'local.conf').stat().st_ino
        backup = self.home / 'backup'
        backup.mkdir()
        journal = {'home': str(self.home), 'entries': []}
        organize.organize(self.home, self.payload, backup, journal)
        self.assertEqual((old / 'local.conf').stat().st_ino, inode)
        self.assertEqual((old / 'local.conf').read_text(), 'private local settings\n')
        self.assertFalse((self.root / 'config/kitty/local.conf').exists())
        deploy.restore(backup)
        self.assertFalse(old.is_symlink())
        self.assertEqual((old / 'local.conf').stat().st_ino, inode)

    def test_conflicting_personal_storage_stops_without_mutation(self):
        for path in (self.home / '.config/kitty', self.home / '.config/enclosure/kitty'):
            path.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'Both personal'):
            organize.plan(self.home, self.payload)
        with self.assertRaisesRegex(ValueError, 'Both personal'):
            deploy.install(self.payload, self.home)
        self.assertFalse((self.home / '.config/kitty').is_symlink())

    def test_relative_external_personal_link_restores_exactly(self):
        external = self.home / 'external-settings'
        external.mkdir()
        (external / 'kitty.conf').write_text('external customization\n')
        original = self.home / '.config/kitty'
        original.parent.mkdir()
        original.symlink_to('../external-settings', target_is_directory=True)
        backup = self.home / 'backup'
        backup.mkdir()
        journal = {'home': str(self.home), 'entries': []}
        organize.organize(self.home, self.payload, backup, journal)
        self.assertEqual((original / 'kitty.conf').read_text(), 'external customization\n')
        deploy.restore(backup)
        import os
        self.assertEqual(os.readlink(original), '../external-settings')
        self.assertEqual((external / 'kitty.conf').read_text(), 'external customization\n')

    def test_nested_relative_external_links_keep_their_original_targets(self):
        import os
        old = self.home / '.config/kitty'
        old.mkdir(parents=True)
        outside = self.home / '.config/shared.conf'
        outside.write_text('shared preferences\n')
        (old / 'shared.conf').symlink_to('../shared.conf')
        (old / 'local.conf').write_text('local\n')
        (old / 'internal.conf').symlink_to('local.conf')
        backup = self.home / 'backup'
        backup.mkdir()
        journal = {'home': str(self.home), 'entries': []}
        organize.organize(self.home, self.payload, backup, journal)
        self.assertEqual((old / 'shared.conf').resolve(), outside)
        self.assertEqual((old / 'internal.conf').read_text(), 'local\n')
        deploy.restore(backup)
        self.assertEqual(os.readlink(old / 'shared.conf'), '../shared.conf')
        self.assertEqual(os.readlink(old / 'internal.conf'), 'local.conf')

    def test_failure_after_grouping_rolls_back_configuration_and_system_paths(self):
        original = self.home / '.config/kitty'
        original.mkdir(parents=True)
        (original / 'kitty.conf').write_text('personal\n')
        with patch.object(organize.shutil, 'copytree', side_effect=OSError('simulated defaults failure')):
            # Start with existing state and exercise deployment's recovery boundary.
            # The organizer itself moves directories without copying their contents.
            backup = self.home / 'backup'
            backup.mkdir()
            journal = {'home': str(self.home), 'entries': []}
            with self.assertRaises(OSError):
                organize.organize(self.home, self.payload, backup, journal)
            deploy.restore(backup)
        self.assertFalse(original.is_symlink())
        self.assertEqual((original / 'kitty.conf').read_text(), 'personal\n')

    def test_managed_source_symlink_and_path_traversal_are_rejected(self):
        (self.root / 'system/bin/example').unlink()
        (self.root / 'system/bin/example').symlink_to('/etc/hostname')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            deploy.verify(self.payload)
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            source(self.payload, '../outside')


if __name__ == '__main__':
    unittest.main()
