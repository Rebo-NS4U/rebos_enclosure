"""Check crash recovery without starting or attaching to any chat backend."""
import importlib.util
from pathlib import Path
import socket
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'system/apps/assistant/scripts/assistant_state.py'
spec = importlib.util.spec_from_file_location('assistant_state', SCRIPT)
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)


class StateTests(unittest.TestCase):
    def test_save_creates_private_directory_and_replaces_complete_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'new/states.json'
            state.save(path, {'assistantSessionChannels': ['chat-one']})
            self.assertEqual(state.load(path, None)['assistantSessionChannels'], ['chat-one'])
            state.save(path, {'assistantSessionChannels': []})
            self.assertEqual(state.load(path, None)['assistantSessionChannels'], [])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertFalse(list(path.parent.glob('.states-*')))

    def test_missing_registry_recovers_live_socket_but_not_stale_socket(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as directory:
            runtime = Path(directory)
            bridges = runtime / 'rebos-assistant'
            bridges.mkdir()
            with socket.socket(socket.AF_UNIX) as live:
                live.bind(str(bridges / 'acp-chat-live.sock'))
                live.listen()
                with socket.socket(socket.AF_UNIX) as stale:
                    stale.bind(str(bridges / 'acp-chat-stale.sock'))
                path = runtime / 'state/states.json'
                recovered = state.load(path, runtime)
                self.assertEqual(recovered['assistantSessionChannels'], ['chat-live'])
                self.assertEqual(recovered['assistantActiveChannel'], 'chat-live')
                state.save(path, {'assistantSessionChannels': []})
                self.assertEqual(state.load(path, runtime)['assistantSessionChannels'], [])
                path.write_text('{broken')
                self.assertEqual(state.load(path, runtime)['assistantSessionChannels'], ['chat-live'])


if __name__ == '__main__':
    unittest.main()
