"""Startup must preserve non-socket paths and leave uncertain listeners alone."""
import errno
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import backend_server
from runtime_socket import prepare_socket, socket_identity, unlink_socket


class RuntimeSocketTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'media.sock'

    def listener(self):
        listener = socket.socket(socket.AF_UNIX)
        self.addCleanup(listener.close)
        listener.bind(str(self.path))
        listener.listen(1)
        return listener

    def test_startup_refuses_regular_file_before_constructing_an_engine(self):
        self.path.write_text('keep this data')
        with patch.object(backend_server.backend, 'Engine') as engine:
            with self.assertRaisesRegex(RuntimeError, 'non-socket'):
                backend_server.BackendServer(self.path).run()
            engine.assert_not_called()
        self.assertEqual(self.path.read_text(), 'keep this data')

    def test_symlinks_are_refused_even_when_the_target_is_missing(self):
        target = self.path.with_name('target')
        self.path.symlink_to(target)
        for exists in (False, True):
            if exists:
                target.write_text('keep target')
            with self.assertRaisesRegex(RuntimeError, 'non-socket'):
                prepare_socket(self.path)
            self.assertTrue(self.path.is_symlink())
        self.assertEqual(target.read_text(), 'keep target')

    def test_live_socket_is_preserved_and_stale_owned_socket_is_removed(self):
        listener = self.listener()
        with self.assertRaisesRegex(RuntimeError, 'already running'):
            prepare_socket(self.path)
        self.assertTrue(self.path.is_socket())
        listener.close()
        prepare_socket(self.path)
        self.assertFalse(self.path.exists())

    def test_foreign_ownership_and_unexpected_probe_errors_do_not_unlink(self):
        self.listener()
        uid = os.getuid()
        with patch('runtime_socket.os.getuid', return_value=uid + 1):
            with self.assertRaisesRegex(RuntimeError, 'foreign-owned'):
                prepare_socket(self.path)
        for code in (errno.EACCES, errno.ETIMEDOUT, errno.EAGAIN):
            with patch('runtime_socket.socket.socket') as factory:
                factory.return_value.__enter__.return_value.connect.side_effect = OSError(code, 'probe failed')
                with self.assertRaisesRegex(RuntimeError, 'safely inspect'):
                    prepare_socket(self.path)
            self.assertTrue(self.path.is_socket())

    def test_shutdown_preserves_a_replacement_file(self):
        listener = self.listener()
        identity = socket_identity(self.path)
        listener.close()
        self.path.unlink()
        self.path.write_text('replacement data')
        self.assertFalse(unlink_socket(self.path, identity))
        self.assertEqual(self.path.read_text(), 'replacement data')
