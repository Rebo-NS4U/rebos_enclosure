import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

spec = importlib.util.spec_from_file_location('deploy', Path(__file__).resolve().parents[1] / 'scripts/deploy.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'new user'
        self.home.mkdir()
        self.payload = self.root / 'payload'
        config = self.payload / 'home/.config/kitty'
        config.mkdir(parents=True)
        (config / 'kitty.conf').write_text('include @HOME@/.cache/colors.conf\n')
        (self.payload / 'manifest.json').write_text(json.dumps({'units': ['.config/kitty']}))
        self.seal()

    def seal(self):
        hashes = {str(p.relative_to(self.payload)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.payload.rglob('*') if p.is_file() and p.name != 'checksums.json'}
        (self.payload / 'checksums.json').write_text(json.dumps(hashes))

    def test_install_and_restore_preserves_source_symlink_and_unrelated_files(self):
        source = self.root / 'original-dotfiles'
        source.mkdir()
        (source / 'kitty.conf').write_text('original')
        config = self.home / '.config'
        config.mkdir()
        (config / 'kitty').symlink_to(source, target_is_directory=True)
        (config / 'unrelated').write_text('keep')
        backup = deploy.install(self.payload, self.home)
        self.assertFalse((config / 'kitty').is_symlink())
        self.assertIn(str(self.home), (config / 'kitty/kitty.conf').read_text())
        self.assertEqual((source / 'kitty.conf').read_text(), 'original')
        deploy.restore(backup)
        self.assertTrue((config / 'kitty').is_symlink())
        self.assertEqual((config / 'unrelated').read_text(), 'keep')

    def test_fresh_install_restore_and_repeat_backups(self):
        first = deploy.install(self.payload, self.home)
        second = deploy.install(self.payload, self.home)
        self.assertNotEqual(first, second)
        deploy.restore(second)
        self.assertTrue((self.home / '.config/kitty/kitty.conf').exists())
        deploy.restore(first)
        self.assertFalse((self.home / '.config/kitty').exists())

    def test_corruption_fails_before_touching_home(self):
        (self.payload / 'home/.config/kitty/kitty.conf').write_text('corrupted')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            deploy.install(self.payload, self.home)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_extra_file_rejected(self):
        (self.payload / 'unexpected').write_text('extra')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            deploy.verify(self.payload)

    def test_parent_symlink_refused_before_write(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.home / '.config').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'real directory'):
            deploy.install(self.payload, self.home)
        self.assertEqual(list(outside.iterdir()), [])

    def test_dry_run_is_read_only(self):
        deploy.install(self.payload, self.home, dry_run=True)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_linked_config_parent_is_copied_and_restored_without_source_changes(self):
        source = self.root / 'dotfiles/environment.d'
        source.mkdir(parents=True)
        (source / 'keep.conf').write_text('preserve')
        (source / '90-rebos.conf').write_text('old value')
        config = self.home / '.config'
        config.mkdir()
        link = config / 'environment.d'
        link.symlink_to('../../dotfiles/environment.d', target_is_directory=True)
        target = self.payload / 'home/.config/environment.d/90-rebos.conf'
        target.parent.mkdir()
        target.write_text('new value')
        (self.payload / 'manifest.json').write_text(json.dumps({'units': ['.config/environment.d/90-rebos.conf']}))
        self.seal()
        deploy.install(self.payload, self.home, dry_run=True)
        self.assertTrue(link.is_symlink())
        self.assertFalse((self.home / '.local').exists())
        backup = deploy.install(self.payload, self.home)
        self.assertFalse(link.is_symlink())
        self.assertEqual((link / 'keep.conf').read_text(), 'preserve')
        self.assertEqual((link / '90-rebos.conf').read_text(), 'new value')
        self.assertEqual((source / '90-rebos.conf').read_text(), 'old value')
        self.assertFalse((source / '90-rebos.conf').is_symlink())
        deploy.restore(backup)
        self.assertTrue(link.is_symlink())
        self.assertEqual(str(link.readlink()), '../../dotfiles/environment.d')
        self.assertEqual((source / '90-rebos.conf').read_text(), 'old value')

    def test_broken_config_parent_link_fails_before_writes(self):
        (self.home / '.config').mkdir()
        (self.home / '.config/kitty').symlink_to(self.root / 'missing')
        target = self.payload / 'home/.config/kitty/new.conf'
        target.write_text('test')
        (self.payload / 'manifest.json').write_text(json.dumps({'units': ['.config/kitty/new.conf']}))
        self.seal()
        with self.assertRaisesRegex(ValueError, 'real directory'):
            deploy.install(self.payload, self.home)
        self.assertFalse((self.home / '.local').exists())

    def test_manifest_traversal_rejected(self):
        (self.payload / 'manifest.json').write_text(json.dumps({'units': ['../outside']}))
        self.seal()
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            deploy.install(self.payload, self.home)

    def test_custom_monitors_plan_and_offload_launcher_restore_together(self):
        scripts = Path(__file__).resolve().parents[1] / 'scripts'
        sys.path.insert(0, str(scripts))
        self.addCleanup(lambda: sys.path.remove(str(scripts)))
        config = self.payload / 'home/.config/niri'
        config.mkdir()
        (config / 'config.kdl').write_text('// installed base\n')
        (self.payload / 'manifest.json').write_text(json.dumps({'units': ['.config/kitty', '.config/niri']}))
        self.seal()
        source = self.root / 'niri-source'
        source.mkdir()
        (source / 'config.kdl').write_text('original untouched')
        (self.home / '.config').mkdir()
        (self.home / '.config/niri').symlink_to(source)
        plan = json.loads(subprocess.check_output(['python3', str(scripts / 'setup.py'), 'plan',
                          '--graphics', 'nvidia-open', '--kernel-headers', 'linux-headers',
                          '--hybrid', '--groups', 'none', '--files-only'], text=True))
        plan['monitors'] = {'layout': 'horizontal', 'outputs': [
            {'name': 'DP-1', 'mode': '3840x2160@144', 'scale': 2},
            {'name': 'HDMI-A-1', 'mode': '1920x1080@60', 'primary': True}]}
        backup = deploy.install(self.payload, self.home, settings=plan)
        installed = self.home / '.config/niri'
        self.assertIn('include "monitors.kdl"', (installed / 'config.kdl').read_text())
        self.assertIn('position x=1920 y=0', (installed / 'monitors.kdl').read_text())
        self.assertEqual((source / 'config.kdl').read_text(), 'original untouched')
        state = self.home / '.local/state/rebos-desktop/installation.json'
        self.assertEqual(state.stat().st_mode & 0o777, 0o600)
        launcher = self.home / '.local/bin/rebos-prime-run'
        self.assertTrue(launcher.stat().st_mode & 0o111)
        deploy.restore(backup)
        self.assertTrue(installed.is_symlink())
        self.assertFalse(state.exists())
        self.assertFalse(launcher.exists())


if __name__ == '__main__':
    unittest.main()
