"""Use real Git snapshots to prove stale launchers run the fresh controller."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipIf(os.geteuid() == 0, 'Updater intentionally refuses root')
class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='rebos-handoff-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.remote = self.base / 'remote'
        self.home = self.base / 'home'
        self.capture = self.base / 'controller-path'
        self.payload = self.remote / 'desktop/payload'
        scripts = self.remote / 'desktop/scripts'
        scripts.parent.mkdir(parents=True)
        shutil.copytree(ROOT / 'desktop/scripts', scripts, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copy2(ROOT / 'update.sh', self.remote / 'update.sh')
        # Never contact the real user's greeter or desktop services in fixtures.
        (scripts / 'greeter_sync.py').write_text('pass\n')
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Update Test')
        self.git('config', 'user.email', 'update@example.invalid')
        units = ['.config/quickshell', '.config/kitty',
                 'code/rebos-assistant/app.py', 'code/anime-streamer/backend_server.py']
        self.payload.mkdir()
        (self.payload / 'manifest.json').write_text(json.dumps({'units': units}))
        self.write_sources('old')
        self.commit('Old snapshot')
        self.stale = self.base / 'stale-checkout'
        subprocess.run(['git', 'clone', str(self.remote), str(self.stale)],
                       check=True, capture_output=True)
        # An old deployment implementation must never be used after handoff.
        old = self.stale / 'desktop/scripts/update.py'
        old.write_text(old.read_text().replace(
            'def apply_fetched_snapshot(snapshot, home, args):',
            "def apply_fetched_snapshot(snapshot, home, args):\n"
            "    raise RuntimeError('STALE CONTROLLER USED')"))
        # This release deliberately contains an obsolete, non-handoff controller.
        controller = scripts / 'update.py'
        latest = controller.read_text()
        controller.write_text("raise RuntimeError('OLD RELEASE CONTROLLER USED')\n")
        self.commit('Historical release')
        self.git('tag', 'v-old')
        controller.write_text(latest.replace(
            'def apply_fetched_snapshot(snapshot, home, args):',
            "def apply_fetched_snapshot(snapshot, home, args):\n"
            "    Path(os.environ['CONTROLLER_CAPTURE']).write_text(__file__)\n"
            "    print('FRESH CONTROLLER ACTIVE', flush=True)"))
        # A separate process must see the updater lock held through handoff.
        probe = """import fcntl, os, pathlib, tempfile
with open(pathlib.Path(tempfile.gettempdir()) / f'rebos-update-{os.getuid()}.lock', 'a') as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(0)
raise SystemExit('Updater lock was lost during handoff')
"""
        controller.write_text(controller.read_text().replace(
            "    print('FRESH CONTROLLER ACTIVE', flush=True)",
            "    print('FRESH CONTROLLER ACTIVE', flush=True)\n"
            f"    subprocess.run([sys.executable, '-c', {probe!r}], check=True)"))
        self.write_sources('new')
        (self.payload / 'home/.config/kitty/new.conf').write_text('new feature')
        self.commit('Future updater and features')
        # Seed one canonical installed copy plus a personal configuration.
        for name, content in {
            '.config/quickshell/shell.qml': 'old',
            '.config/kitty/kitty.conf': 'old default',
            '.config/kitty/personal.conf': 'my font and shortcuts',
            'code/rebos-assistant/app.py': 'FEATURE = "old"\n',
            'code/anime-streamer/backend_server.py': 'FEATURE = "old"\n',
        }.items():
            target = self.home / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        defaults = self.home / '.local/state/rebos-desktop/preference-defaults.json'
        defaults.parent.mkdir(parents=True)
        defaults.write_text(json.dumps({
            '.config/kitty/kitty.conf': hashlib.sha256(b'old default').hexdigest(),
            '.config/kitty/personal.conf': hashlib.sha256(b'old personal default').hexdigest(),
        }))
        self.environment = {**os.environ, 'HOME': str(self.home),
                            'CONTROLLER_CAPTURE': str(self.capture)}
        for name in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME'):
            self.environment.pop(name, None)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.remote), *args],
                                       stderr=subprocess.PIPE, text=True).strip()

    def write_sources(self, version):
        files = {'.config/quickshell/shell.qml': version,
                 '.config/kitty/kitty.conf': version + ' default',
                 '.config/kitty/personal.conf': version + ' personal default',
                 'code/rebos-assistant/app.py': f'FEATURE = "{version}"\n',
                 'code/anime-streamer/backend_server.py': f'FEATURE = "{version}"\n'}
        for name, content in files.items():
            target = self.payload / 'home' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

    def commit(self, message):
        hashes = {str(p.relative_to(self.payload)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.payload.rglob('*') if p.is_file() and p.name != 'checksums.json'}
        (self.payload / 'checksums.json').write_text(json.dumps(hashes))
        self.git('add', '.')
        self.git('commit', '-qm', message)

    def run_update(self, *args, repository=None):
        return subprocess.run(['bash', str(self.stale / 'update.sh'), '--repository',
                               str(repository or self.remote), '--files-only', *args],
                              env=self.environment, capture_output=True, text=True, timeout=25)

    def test_stale_dirty_checkout_uses_fresh_controller_without_duplicate_installations(self):
        old_head = subprocess.check_output(['git', '-C', str(self.stale), 'rev-parse', 'HEAD'])
        for args in (['--dry-run'], [], []):
            result = self.run_update(*args)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('FRESH CONTROLLER ACTIVE', result.stdout)
            self.assertFalse(Path(self.capture.read_text()).exists(), 'Temporary controller is removed')
        self.assertEqual((self.home / '.config/quickshell/shell.qml').read_text(), 'new')
        self.assertEqual((self.home / '.config/kitty/kitty.conf').read_text(), 'new default')
        self.assertEqual((self.home / '.config/kitty/personal.conf').read_text(), 'my font and shortcuts')
        self.assertEqual((self.home / '.config/kitty/new.conf').read_text(), 'new feature')
        for relative in ('.config/quickshell', 'code/rebos-assistant', 'code/anime-streamer'):
            self.assertFalse((self.home / relative).is_symlink())
        self.assertEqual(subprocess.check_output(['git', '-C', str(self.stale), 'rev-parse', 'HEAD']), old_head)
        self.assertEqual((self.stale / 'desktop/payload/home/.config/quickshell/shell.qml').read_text(), 'old')

    def test_old_release_uses_current_controller_but_pins_requested_features(self):
        # A branch named like the release must not substitute for its tag.
        self.git('branch', 'v-old')
        result = self.run_update('--release', 'v-old')
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn('FRESH CONTROLLER ACTIVE', result.stdout)
        self.assertEqual((self.home / '.config/quickshell/shell.qml').read_text(), 'old')
        self.assertEqual((self.home / '.config/kitty/personal.conf').read_text(), 'my font and shortcuts')
        self.assertFalse(Path(self.capture.read_text()).exists())

    def test_fetch_failure_never_uses_stale_controller_or_changes_installation(self):
        result = self.run_update(repository=self.base / 'missing-remote')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('STALE CONTROLLER USED', result.stderr)
        self.assertFalse(self.capture.exists())
        self.assertEqual((self.home / '.config/quickshell/shell.qml').read_text(), 'old')
        self.assertFalse((self.home / '.local/state/rebos-desktop/backups').exists())

    def test_missing_release_stops_without_touching_installed_files(self):
        result = self.run_update('--release', 'v-missing')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.capture.exists())
        self.assertEqual((self.home / '.config/quickshell/shell.qml').read_text(), 'old')
        self.assertFalse((self.home / '.local/state/rebos-desktop/backups').exists())

    def test_fresh_controller_keeps_guard_against_modified_installed_code(self):
        code = self.home / 'code/rebos-assistant/app.py'
        record = self.home / '.local/state/rebos-desktop/source.json'
        record.write_text(json.dumps({'files': {
            'code/rebos-assistant/app.py': hashlib.sha256(code.read_bytes()).hexdigest()}}))
        code.write_text('MY_LOCAL_FIX = True\n')
        result = self.run_update()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Installed managed files changed', result.stderr)
        self.assertEqual(code.read_text(), 'MY_LOCAL_FIX = True\n')
        self.assertFalse((self.home / '.local/state/rebos-desktop/backups').exists())
