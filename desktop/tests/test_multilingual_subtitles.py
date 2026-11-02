"""Regression checks for the shipped multilingual subtitle worker."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'payload/home/code/anime-streamer'))
import menu_backend
from live_subtitles import LiveSubtitles, cues_from_whisper, recognize

class SpanishCaptionTests(unittest.TestCase):
    def test_auto_detection_changes_language_between_speech_spans(self):
        import subprocess
        import wave
        from live_subtitles import BINARY, SPANISH_MODEL
        calls = []
        progress = []
        with tempfile.TemporaryDirectory() as folder:
            wav = Path(folder) / 'mixed.wav'
            with wave.open(str(wav), 'wb') as audio:
                audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\0' * 16000 * 2 * 10)
            def run(command, **kwargs):
                if command[0] != str(BINARY):
                    return subprocess.CompletedProcess(command, 0,
                        b'Speech segment 0: start = 200, end = 400\nSpeech segment 1: start = 700, end = 900', b'')
                calls.append(command)
                prefix = Path(command[command.index('-of') + 1])
                prefix.with_suffix('.json').write_text(json.dumps({
                    'result': {'language': 'en' if len(calls) == 1 else 'es'},
                    'transcription': [{'text': 'Hello world.', 'offsets': {'from': 0, 'to': 2000},
                        'tokens': [{'text': ' Hello', 'offsets': {'from': 500, 'to': 900}},
                                   {'text': ' world.', 'offsets': {'from': 1000, 'to': 1300}}]}]}))
                return subprocess.CompletedProcess(command, 0, b'', b'')
            cues = cues_from_whisper(recognize(wav, Path(folder) / 'auto', run=run, language='auto',
                                               on_progress=lambda data: progress.append((len(calls), len(data['transcription'])))), 32)
            self.assertEqual(progress, [(1, 1), (2, 2)])
            self.assertEqual(cues[0][0], 34.5)  # English keeps word timing.
            self.assertEqual(cues[1], (39, 41, 'Hello world.'))  # Spanish uses speech timing.
            self.assertEqual(len(calls), 2)
            for command in calls:
                self.assertIn('--translate', command)
                self.assertEqual(command[command.index('-l') + 1], 'auto')
                self.assertEqual(command[command.index('-m') + 1], str(SPANISH_MODEL))

    def test_translation_uses_speech_spans_instead_of_reordered_token_times(self):
        import subprocess
        import wave
        from live_subtitles import SPANISH_MODEL, BINARY
        commands = []
        with tempfile.TemporaryDirectory() as folder:
            wav = Path(folder) / 'speech.wav'
            with wave.open(str(wav), 'wb') as audio:
                audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\0' * 16000 * 2 * 10)
            def run(command, **kwargs):
                commands.append(command)
                if command[0] != str(BINARY):
                    return subprocess.CompletedProcess(command, 0,
                        b'Speech segment 0: start = 200, end = 400\nSpeech segment 1: start = 700, end = 900', b'')
                prefix = Path(command[command.index('-of') + 1])
                prefix.with_suffix('.json').write_text(json.dumps({'transcription': [{
                    'text': 'Hello world.', 'offsets': {'from': 0, 'to': 0},
                    'tokens': [{'text': 'Wrong token timing', 'offsets': {'from': 0, 'to': 1}}]}]}))
                return subprocess.CompletedProcess(command, 0, b'', b'')
            data = recognize(wav, Path(folder) / 'translated', run=run, language='es')
            self.assertEqual(cues_from_whisper(data, 32),
                             [(34, 36, 'Hello world.'), (39, 41, 'Hello world.')])
            for command in commands[1:]:
                self.assertIn('--translate', command)
                self.assertEqual(command[command.index('-l') + 1], 'es')
                self.assertEqual(command[command.index('-m') + 1], str(SPANISH_MODEL))
            self.assertFalse(list(Path(folder).glob('*-speech-*')))

    def test_language_switch_replaces_captions_without_restarting_player(self):
        engine = menu_backend.Engine()
        old = Mock(language='en')
        engine.captions = old
        engine.session = Mock()
        engine.links = ['https://example.test/video', '', '', '']
        engine.file_loaded = True
        engine.settings.update(live_subtitles=True, caption_language='es', caption_delay=1.5)
        with patch.object(menu_backend, 'LiveSubtitles') as factory, patch.object(menu_backend, 'send'), patch.object(engine, 'prefetch_next'):
            engine.settings_changed()
            old.close.assert_called_once()
            engine.session.clear_captions.assert_called_once()
            self.assertEqual(factory.call_args.kwargs['language'], 'es')
            self.assertEqual(factory.call_args.kwargs['delay'], 1.5)
            engine.session.load.assert_not_called()
            engine.session.close.assert_not_called()

    def test_missing_spanish_model_reports_the_required_file(self):
        with patch('live_subtitles.SPANISH_MODEL', Path('/missing/ggml-base.bin')):
            with self.assertRaisesRegex(RuntimeError, 'ggml-base.bin'):
                LiveSubtitles(['video', '', '', ''], '/tmp', lambda _: None, lambda _: None, language='es')


class CaptionReadinessTests(unittest.TestCase):
    def test_old_captions_do_not_claim_current_scene_is_ready(self):
        worker = LiveSubtitles.__new__(LiveSubtitles)
        worker.position = 32
        worker.delay = 0
        worker.language = 'auto'
        worker.blocks = {0: [(0, 1, 'Old speech')]}
        worker.last_status = None
        worker.on_status = Mock()
        worker.post = lambda callback, value: callback(value)
        worker.publish_status()
        worker.on_status.assert_called_once_with('Generating captions for the current scene…')
        worker.blocks[4] = []
        worker.publish_status()
        worker.on_status.assert_called_with('No speech detected in the current scene')
        worker.blocks[4] = [(32, 35, 'Current speech')]
        worker.publish_status()
        worker.on_status.assert_called_with('Auto language → English captions ready')
        worker.on_status.reset_mock()
        worker.publish_status()
        worker.on_status.assert_not_called()

    def test_font_selection_is_saved_and_unknown_font_is_rejected(self):
        import app
        engine = Mock(settings=dict(app.DEFAULTS))
        with patch.object(menu_backend, 'engine', engine), patch.object(app, 'save_json') as save, patch.object(menu_backend, 'send'):
            menu_backend.dispatch({'action': 'settings', 'settings': {'subtitle_font': 'Noto Sans'}})
            self.assertEqual(engine.settings['subtitle_font'], 'Noto Sans')
            save.assert_called_with(app.CONFIG, engine.settings)
            menu_backend.dispatch({'action': 'settings', 'settings': {'subtitle_font': '--bad-font'}})
            self.assertEqual(engine.settings['subtitle_font'], 'Noto Sans')


class CaptionSchedulingTests(unittest.TestCase):
    def test_resume_starts_worker_at_playback_position(self):
        with patch('live_subtitles.threading.Thread') as thread, patch.object(Path, 'is_file', return_value=True), tempfile.TemporaryDirectory() as folder:
            worker = LiveSubtitles(['video', '', '', ''], folder, Mock(), Mock(),
                                   position=1234, duration=2400)
            thread.return_value.start.assert_called_once()
            self.assertEqual(worker.position, 1234)
            self.assertEqual(worker.duration, 2400)

    def test_worker_builds_ahead_instead_of_chasing_expired_dialogue(self):
        import threading
        from live_subtitles import CHUNK, LOOKAHEAD
        worker = LiveSubtitles.__new__(LiveSubtitles)
        worker.cancelled = False
        worker.language = 'auto'
        worker.condition = threading.Condition()
        worker.position = 100
        worker.duration = 200
        worker.processing_seconds = 8
        worker.blocks = {}
        worker.partial = {}
        worker.attempts = {}
        worker.post = Mock()
        worker.on_status = Mock()
        worker.publish = Mock()
        generated = []
        def transcribe(block):
            generated.append(block * CHUNK)
            worker.cancelled = True
            return []
        worker.transcribe = transcribe
        worker.work()
        self.assertGreater(generated[0], worker.position)
        self.assertLessEqual(generated[0], worker.position + LOOKAHEAD)
