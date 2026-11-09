"""Reader speech selection, speed, asset integrity, and cancellation."""
import argparse
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch, Mock, MagicMock

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/reader_speech.py'
spec = importlib.util.spec_from_file_location('reader_speech', SOURCE)
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)

def fake_engine():
    engine = Mock()
    engine.tokenizer.phonemize.side_effect = lambda text, *args: text
    engine.tokenizer.tokenize.side_effect = lambda text: list(range(len(text)))
    engine.get_voice_style.return_value = MagicMock()
    def run(names, inputs):
        duration = Mock()
        duration.flatten.return_value = [1] * len(inputs['tokens'][0])
        return 'samples', duration
    engine.sess.run.side_effect = run
    return engine


class SpeechTests(unittest.TestCase):
    def setUp(self):
        model = patch.object(speech, 'timing_model', return_value=Path('/unused/timed.onnx'))
        model.start()
        self.addCleanup(model.stop)

    def test_preloaded_audio_reuses_synthesis_and_retains_word_cues(self):
        engine = fake_engine()
        module = types.SimpleNamespace(Kokoro=Mock(return_value=engine))
        numpy = MagicMock()
        numpy.clip.return_value.__mul__.return_value.astype.return_value.tobytes.return_value = b'\x01\x00' * 100
        text = 'First page.\n\nNext 😀 paragraph.'
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'XDG_RUNTIME_DIR': tmp}), patch.dict(sys.modules, {'kokoro_onnx': module, 'numpy': numpy}), patch.object(speech, 'play_audio') as play:
            speech.render_kokoro(text, Path('/unused'), options=speech.RenderOptions(prepare=True))
            play.assert_not_called()
            self.assertEqual(engine.sess.run.call_count, 2)
            module.Kokoro.side_effect = AssertionError('Cached playback loaded the model')
            speech.render_kokoro(text, Path('/unused'))
            chunks = play.call_args.args[0]
            self.assertEqual(chunks[0].data, b'\x01\x00' * 100)
            self.assertEqual(len(chunks[1].data), round(24000 * .12 / 1.05) * 2)
            self.assertEqual(chunks[2].cues[0][1], len('First page.\n\n'))
            key = speech.cached_page(text, 'kokoro-heart', 1.05, [])
            for other in [speech.cached_page(text, 'kokoro-bella', 1.05, []), speech.cached_page(text, 'kokoro-heart', 1.2, []), speech.cached_page(text + 'changed', 'kokoro-heart', 1.05, []), speech.cached_page(text, 'kokoro-heart', 1.05, [4])]:
                self.assertNotEqual(key, other)
                self.assertIsNone(speech.read_cached_page(other))
            for i in range(5):
                speech.store_cached_page(speech.cached_page(str(i), 'kokoro-heart', 1.05, []), chunks)
            self.assertEqual(len(list(key.parent.glob('*.json'))), 3)

    def test_ready_requires_runtime_and_both_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for relative in ['venv/bin/python'] + ['kokoro/' + name for name in speech.KOKORO_ASSETS]:
                self.assertFalse(speech.ready(directory))
                path = directory / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            self.assertTrue(speech.ready(directory))

    def test_speed_validation(self):
        self.assertEqual(speech.speaking_speed('1.15'), 1.15)
        for value in ('nan', 'inf', '0', '2.1'):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                speech.speaking_speed(value)

    def test_worker_gets_speed_and_text_without_shell(self):
        text = '--help; $(touch /tmp/never-run)'
        with patch.object(sys, 'argv', ['reader_speech.py', '--speed', '1.2', '--', text]), patch.object(speech, 'ready', return_value=True), patch.object(speech.os, 'execv') as execute:
            speech.main()
        command = execute.call_args.args[1]
        self.assertEqual(command[command.index('--speed') + 1], '1.2')
        self.assertEqual(command[-2:], ['--', text])

    def test_missing_voice_does_not_download_or_fallback(self):
        with patch.object(sys, 'argv', ['reader_speech.py', '--', 'Hello']), patch.object(speech, 'ready', return_value=False), patch.object(speech, 'setup') as setup:
            with self.assertRaisesRegex(RuntimeError, 'Download voices'):
                speech.main()
        setup.assert_not_called()

    def test_all_selected_voices_preserve_pitch_and_speed(self):
        import wave
        for profile, (voice, _) in speech.PROFILES.items():
            with self.subTest(profile=profile):
                engine = fake_engine()
                module = types.SimpleNamespace(Kokoro=Mock(return_value=engine))
                numpy = MagicMock()
                numpy.clip.return_value.__mul__.return_value.astype.return_value.tobytes.return_value = b'\x01\x00' * 100
                with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {'kokoro_onnx': module, 'numpy': numpy}):
                    output = Path(tmp) / 'voice.wav'
                    speech.render_kokoro('A sentence.', Path('/unused'), output, profile, options=speech.RenderOptions(speed=1.15))
                    with wave.open(str(output)) as wav:
                        self.assertEqual(wav.getframerate(), 24000)
                        self.assertEqual(wav.getnframes(), 100)
                engine.get_voice_style.assert_called_once_with(voice)
                numpy.array.assert_called_once_with([1.15], dtype=numpy.float32)
                engine.tokenizer.phonemize.assert_any_call('A sentence.', 'en-us')

    def test_connected_sentences_abbreviations_and_decimals_stay_together(self):
        text = 'Dr. Smith paid $3.50. "Really?" she asked. Yes, he replied.'
        self.assertEqual(speech.narration_units(text), [(0, text, 0.0)])

    def test_real_paragraphs_pause_and_keep_source_offsets(self):
        text = '😀 First paragraph. Next paragraph follows.'
        position = text.index('Next')
        utf16 = len(text[:position].encode('utf-16-le')) // 2
        units = speech.narration_units(text, [utf16])
        self.assertEqual(units, [(0, '😀 First paragraph.', 0.12), (position, 'Next paragraph follows.', 0.0)])
        self.assertEqual(len(speech.narration_units('One line.\n\nAnother paragraph.')), 2)

    def test_bounded_chunks_do_not_drop_or_duplicate_text(self):
        text = ('A long sentence with commas, and words that must stay in order; ' * 40).strip()
        units = speech.narration_units(text)
        self.assertTrue(all(len(body) <= 180 for _, body, _ in units))
        self.assertEqual(' '.join(body for _, body, _ in units).split(), text.split())
        self.assertEqual(units[-1][2], 0)

    def test_next_chunk_is_prepared_while_playback_is_busy(self):
        generated = threading.Event()
        def chunks():
            yield b'\x01\x00'
            generated.set()
            yield b'\x02\x00'
        player = Mock()
        player.wait.return_value = 0
        player.poll.return_value = 0
        player.stdin.write.side_effect = lambda data: self.assertTrue(generated.wait(2), 'Next chunk was not prepared during playback')
        with patch.object(speech.subprocess, 'Popen', return_value=player):
            speech.play_audio(chunks(), 24000)
        self.assertEqual(player.stdin.write.call_count, 2)

    def test_paragraph_silence_does_not_block_speech_lookahead(self):
        prepared = threading.Event()
        def chunks():
            yield speech.TimedAudio(b'\1\0', [])
            yield b'\0\0'
            yield speech.TimedAudio(b'\2\0', [])
            yield b'\0\0'
            prepared.set()
            yield speech.TimedAudio(b'\3\0', [])
        player = Mock()
        player.wait.return_value = 0
        player.poll.return_value = 0
        player.stdin.write.side_effect = lambda data: self.assertTrue(prepared.wait(2), 'Paragraph silence blocked synthesis lookahead')
        with patch.object(speech.subprocess, 'Popen', return_value=player):
            speech.play_audio(chunks(), 24000)
        self.assertEqual(player.stdin.write.call_count, 5)

    def test_short_opener_waits_for_following_speech_before_playback(self):
        generated = []
        def chunks():
            for index, seconds in enumerate((0.5, 0.12, 8, 8)):
                generated.append(index)
                yield speech.TimedAudio(b'\0\0' * round(100 * seconds), [])
        stream = speech.buffered_start(chunks(), 100)
        next(stream)
        self.assertEqual(generated, [0, 1, 2])
        list(stream)
        self.assertEqual(generated, [0, 1, 2, 3])

    def test_startup_reserve_is_bounded_and_preserves_short_selection(self):
        tiny = [speech.TimedAudio(b'\0\0', []) for _ in range(100)]
        generated = []
        def chunks():
            for chunk in tiny:
                generated.append(chunk)
                yield chunk
        stream = speech.buffered_start(chunks(), 24000)
        next(stream)
        self.assertEqual(len(generated), 12)
        self.assertEqual(list(speech.buffered_start(tiny[:1], 24000)), tiny[:1])
        with self.assertRaisesRegex(RuntimeError, 'synthesis failed'):
            def broken():
                yield tiny[0]
                raise RuntimeError('synthesis failed')
            next(speech.buffered_start(broken(), 24000))

    def test_wrapped_lines_are_spoken_as_spaces_with_original_word_cues(self):
        engine = fake_engine()
        module = types.SimpleNamespace(Kokoro=Mock(return_value=engine))
        numpy = MagicMock()
        numpy.clip.return_value.__mul__.return_value.astype.return_value.tobytes.return_value = b'\x01\x00' * 100
        text = '😀 First line\ncontinues here.'
        with patch.dict(sys.modules, {'kokoro_onnx': module, 'numpy': numpy}):
            chunk = list(speech.kokoro_chunks(text, Path('/unused'), 'kokoro-heart', 1.05, []))[0]
        engine.tokenizer.phonemize.assert_any_call(text.replace('\n', ' '), 'en-us')
        self.assertEqual(chunk.cues, speech.aligned_cues(text, text.replace('\n', ' '), [1] * (len(text) + 2), lambda word: word))

    def test_pause_freezes_clock_and_signals_only_the_audio_player(self):
        control = speech.PlaybackControl()
        player = Mock()
        player.poll.return_value = None
        with patch.object(speech.time, 'monotonic', return_value=10) as clock:
            control.attach(player)
            clock.return_value = 12
            control.set_paused(True)
            clock.return_value = 20
            self.assertEqual(control.now(), 12)
            control.set_paused(True)
            clock.return_value = 25
            control.set_paused(False)
            clock.return_value = 30
            self.assertEqual(control.now(), 17)
        self.assertEqual([call.args[0] for call in player.send_signal.call_args_list], [signal.SIGSTOP, signal.SIGCONT])

    def test_ordered_commands_can_pause_before_player_creation(self):
        control = speech.PlaybackControl()
        with patch.object(sys, 'stdin', io.StringIO('pause\nresume\npause\n')):
            control.read_commands()
        player = Mock()
        player.poll.return_value = None
        control.attach(player)
        player.send_signal.assert_called_once_with(signal.SIGSTOP)
        with patch.object(sys, 'stdin', io.StringIO('resume\n')):
            control.read_commands()
        self.assertEqual(player.send_signal.call_args.args[0], signal.SIGCONT)

    def test_corrupt_download_is_not_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'voices-v1.0.bin'
            with patch.object(speech.urllib.request, 'urlopen', return_value=io.BytesIO(b'bad')):
                with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
                    speech.download_model(target, hashlib.sha256(b'correct').hexdigest())
            self.assertFalse(target.exists())
            self.assertFalse(target.with_suffix('.bin.part').exists())

    def test_cancel_terminates_player_and_restores_signal(self):
        def chunks():
            yield b'\x01\x00'
        player = Mock()
        player.stdin.write.side_effect = lambda data: signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        player.poll.return_value = None
        player.wait.side_effect = [subprocess.TimeoutExpired('pw-play', 2), 0]
        previous = signal.getsignal(signal.SIGTERM)
        with patch.object(speech.subprocess, 'Popen', return_value=player), self.assertRaises(SystemExit):
            speech.play_audio(chunks(), 24000)
        player.terminate.assert_called_once()
        player.kill.assert_called_once()
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)

if __name__ == '__main__':
    unittest.main()
