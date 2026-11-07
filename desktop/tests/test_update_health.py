"""Reject broken snapshot code before package changes or desktop replacement."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update
import update_health

APP = Path(__file__).resolve().parents[2] / 'system/apps/assistant'


class UpdateHealthTests(unittest.TestCase):
    def test_bad_python_does_not_reach_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary)
            source = snapshot / 'desktop/payload/home/broken.py'
            source.parent.mkdir(parents=True)
            source.write_text('def broken(:')
            with patch.object(update, 'verify'), patch.object(update, 'install') as install:
                with self.assertRaises(SyntaxError):
                    update.apply_snapshot(snapshot, snapshot / 'home', dry_run=True)
                install.assert_not_called()

    def test_invalid_shell_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            payload = Path(temporary)
            (payload / 'home').mkdir()
            (payload / 'home/broken.sh').write_text('if then\n')
            with self.assertRaisesRegex(ValueError, 'Invalid shell script'):
                update_health.validate(payload)

    def test_missing_provider_support_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            payload = Path(temporary)
            scripts = payload / 'home/code/rebos-assistant/scripts'
            scripts.mkdir(parents=True)
            (scripts.parent / 'shell.qml').touch()
            (scripts / 'google_agent.py').touch()
            with patch.object(update_health.shutil, 'which', return_value='/usr/bin/qs'):
                with self.assertRaisesRegex(ValueError, 'google_settings.json'):
                    update_health.validate(payload)

    @unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
    def test_incompatible_sidebar_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            payload = Path(temporary)
            app = payload / 'home/code/rebos-assistant'
            shutil.copytree(APP, app)
            selector = app / 'modules/sidebar/ModelSelectorPopup.qml'
            selector.write_text(selector.read_text().replace('property bool agentSelection: true', 'property bool removedProperty: true'))
            with self.assertRaisesRegex(ValueError, 'agentSelection'):
                update_health.validate(payload)

class LocalChangeTests(unittest.TestCase):
    def test_only_edits_equal_to_verified_incoming_files_are_accepted(self):
        import hashlib
        import json
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home, payload = root / 'home', root / 'payload'
            relative = 'code/app.py'
            code, incoming = home / relative, payload / 'home' / relative
            code.parent.mkdir(parents=True)
            incoming.parent.mkdir(parents=True)
            incoming.write_text('home = "@HOME@"\n')
            code.write_text('home = "' + str(home) + '"\n')
            record = home / '.local/state/rebos-desktop/source.json'
            record.parent.mkdir(parents=True)
            record.write_text(json.dumps({'files': {relative: 'old-deployment-hash'}}))
            (payload / 'manifest.json').write_text(json.dumps({'units': [relative]}))
            hashes = {str(p.relative_to(payload)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in payload.rglob('*') if p.is_file()}
            (payload / 'checksums.json').write_text(json.dumps(hashes))
            update.check_local_changes(home, payload)
            code.write_text('unsaved local change')
            with self.assertRaisesRegex(ValueError, relative):
                update.check_local_changes(home, payload)
            code.unlink()
            with self.assertRaisesRegex(ValueError, relative):
                update.check_local_changes(home, payload)
            code.write_text('home = "' + str(home) + '"\n')
            incoming.write_text('unverified incoming edit')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                update.check_local_changes(home, payload)

    def test_modified_managed_code_blocks_update_but_preferences_do_not(self):
        import hashlib
        import json
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            code = home / 'code/app.py'
            code.parent.mkdir()
            code.write_text('original')
            record = home / '.local/state/rebos-desktop/source.json'
            record.parent.mkdir(parents=True)
            record.write_text(json.dumps({'files': {
                'code/app.py': hashlib.sha256(code.read_bytes()).hexdigest()}}))
            preference = home / '.config/theme.json'
            preference.parent.mkdir()
            preference.write_text('personal theme')
            update.check_local_changes(home)
            code.write_text('unsaved fix')
            with self.assertRaisesRegex(ValueError, 'code/app.py'):
                update.check_local_changes(home)
            code.unlink()
            with self.assertRaisesRegex(ValueError, 'code/app.py'):
                update.check_local_changes(home)


if __name__ == '__main__':
    unittest.main()
