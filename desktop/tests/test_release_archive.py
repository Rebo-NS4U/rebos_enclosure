"""Committed-source exports carry deterministic checksums and preserve existing paths."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'desktop/scripts'))
SPEC = importlib.util.spec_from_file_location('release_snapshot', ROOT / 'desktop/scripts/snapshot.py')
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)


class ReleaseArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / 'portable.txt').write_text('committed portable source')
        subprocess.run(['git', '-C', str(self.repo), 'add', 'portable.txt'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Release Test',
                        '-c', 'user.email=release@example.invalid', 'commit', '-qm', 'Fixture'], check=True)
        self.output = self.root / 'candidate.tar.gz'

    def test_export_is_reproducible_and_excludes_uncommitted_personal_files(self):
        (self.repo / 'portable.txt').write_text('uncommitted edit')
        (self.repo / 'account.txt').write_text('synthetic private fixture')
        with patch.object(snapshot, 'ROOT', self.repo):
            snapshot.export(self.output)
            second = self.root / 'second.tar.gz'
            snapshot.export(second)
        self.assertEqual(self.output.read_bytes(), second.read_bytes())
        with tarfile.open(self.output) as archive:
            self.assertEqual(archive.getnames(), ['portable.txt'])
            self.assertEqual(archive.extractfile('portable.txt').read(), b'committed portable source')
        digest = hashlib.sha256(self.output.read_bytes()).hexdigest()
        self.assertEqual(self.output.with_name(self.output.name + '.sha256').read_text(), digest + '  candidate.tar.gz\n')

    def test_existing_archive_checksum_and_dangling_links_are_preserved(self):
        for occupied in (self.output, self.output.with_name(self.output.name + '.sha256')):
            occupied.write_text('keep existing bytes')
            with self.assertRaises(ValueError), patch.object(snapshot, 'ROOT', self.repo):
                snapshot.export(self.output)
            self.assertEqual(occupied.read_text(), 'keep existing bytes')
            occupied.unlink()
        missing = self.root / 'missing'
        self.output.symlink_to(missing)
        with self.assertRaises(ValueError), patch.object(snapshot, 'ROOT', self.repo):
            snapshot.export(self.output)
        self.assertFalse(missing.exists())
        self.assertTrue(self.output.is_symlink())
