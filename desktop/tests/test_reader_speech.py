"""Verify offline selection and cleanup of the reader's audio subprocess."""
import importlib.util
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, Mock

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/reader_speech.py'
spec = importlib.util.spec_from_file_location('reader_speech', SOURCE)
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)


class SpeechTests(unittest.TestCase):
    def test_ready_requires_runtime_and_both_voice_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for relative in ('venv/bin/python', f'voices/{speech.VOICE}.onnx', f'voices/{speech.VOICE}.onnx.json'):
                self.assertFalse(speech.ready(directory))
                target = directory / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch()
            self.assertTrue(speech.ready(directory))

    def test_fallback_never_downloads_or_interprets_text(self):
        text = '--help; $(touch /tmp/should-never-run)'
        with patch.object(sys, 'argv', ['reader_speech.py', '--', text]), \
             patch.object(speech, 'ready', return_value=False), \
             patch.object(speech.os, 'execvp') as execute, patch.object(speech, 'setup') as setup:
            speech.main()
        execute.assert_called_once_with('espeak-ng', ['espeak-ng', '-s', '165', '--', text])
        setup.assert_not_called()

    def test_natural_voice_executes_worker_directly(self):
        with patch.object(sys, 'argv', ['reader_speech.py', '--', 'Hello']), \
             patch.object(speech, 'ready', return_value=True), patch.object(speech.os, 'execv') as execute:
            speech.main()
        command = execute.call_args.args[1]
        self.assertEqual(command[-3:], ['--worker', '--', 'Hello'])
        self.assertEqual(command[0], str(speech.data_dir() / 'venv/bin/python'))

    def test_cancel_cleans_up_player_even_if_termination_times_out(self):
        voice = Mock()
        voice.config.sample_rate = 22050
        def chunks(text):
            # Simulate the same signal Quickshell sends when Stop is pressed.
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            yield None
        voice.synthesize = chunks
        player = Mock()
        player.poll.return_value = None
        player.wait.side_effect = [subprocess.TimeoutExpired('pw-play', 2), 0]
        piper = types.SimpleNamespace(PiperVoice=Mock())
        piper.PiperVoice.load.return_value = voice
        previous = signal.getsignal(signal.SIGTERM)
        with patch.dict(sys.modules, {'piper': piper}), patch.object(speech.subprocess, 'Popen', return_value=player):
            with self.assertRaises(SystemExit):
                speech.render('Hello', Path('/unused'))
        player.terminate.assert_called_once()
        player.kill.assert_called_once()
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)


if __name__ == '__main__':
    unittest.main()
