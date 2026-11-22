"""Regression checks for the shipped multilingual subtitle worker."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'system/apps/media'))
import menu_backend
from menu_requests import MenuRequest
from live_subtitles import LiveSubtitles, CaptionOptions, cues_from_whisper, recognize, speech_spans

class SpeechSpanTests(unittest.TestCase):
    def test_group_nearby_english_speech_and_preserve_long_pauses(self):
        output = (b'Speech segment 0: start = 20, end = 100\n'
                  b'Speech segment 1: start = 180, end = 300\n'
                  b'Speech segment 2: start = 450, end = 620')
        self.assertEqual(speech_spans(output, 'en'), [(0.2, 3), (4.5, 6.2)])
        for language in ('es', 'auto'):
            self.assertEqual(speech_spans(output, language), [(0.2, 1), (1.8, 3), (4.5, 6.2)])
        self.assertEqual(speech_spans(b'No speech', 'en'), [])


class CaptionMixTests(unittest.TestCase):
    def test_center_audio_is_added_only_during_detected_speech(self):
        import struct
        import wave
        from live_subtitles import caption_mix

        rate = 16000
        stereo = struct.pack('<hh', 100, 900) * rate
        with tempfile.TemporaryDirectory() as folder:
            probe = Path(folder) / 'center.wav'
            with wave.open(str(probe), 'wb') as output:
                output.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
                params = output.getparams()
            detector = Mock(return_value=Mock(returncode=0, stdout=b'Speech segment 0: start = 25, end = 75'))
            samples = struct.unpack(f'<{rate}h', caption_mix(stereo, params, probe, detector))
            self.assertEqual(samples[rate // 8], 100)
            self.assertEqual(samples[rate // 2], 500)
            self.assertEqual(samples[7 * rate // 8], 100)

            detector.side_effect = RuntimeError('Center probe failed')
            self.assertEqual(caption_mix(stereo, params, probe, detector), struct.pack('<h', 100) * rate)


class TranslatedCaptionTests(unittest.TestCase):
    def test_auto_detection_changes_language_between_speech_spans(self):
        import subprocess
        import wave
        from live_subtitles import BINARY, MULTILINGUAL_MODEL
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
                self.assertEqual(command[command.index('-m') + 1], str(MULTILINGUAL_MODEL))

    def test_translation_uses_speech_spans_instead_of_reordered_token_times(self):
        import subprocess
        import wave
        from live_subtitles import MULTILINGUAL_MODEL, BINARY
        commands = []
        clip_lengths = []
        with tempfile.TemporaryDirectory() as folder:
            wav = Path(folder) / 'speech.wav'
            with wave.open(str(wav), 'wb') as audio:
                audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\0' * 16000 * 2 * 10)
            def run(command, **kwargs):
                commands.append(command)
                if command[0] != str(BINARY):
                    return subprocess.CompletedProcess(command, 0,
                        b'Speech segment 0: start = 200, end = 290\n'
                        b'Speech segment 1: start = 310, end = 400\n'
                        b'Speech segment 2: start = 700, end = 900', b'')
                with wave.open(command[command.index('-f') + 1], 'rb') as clip:
                    clip_lengths.append(clip.getnframes())
                prefix = Path(command[command.index('-of') + 1])
                prefix.with_suffix('.json').write_text(json.dumps({'transcription': [{
                    'text': 'Hello world.', 'offsets': {'from': 0, 'to': 0},
                    'tokens': [{'text': 'Wrong token timing', 'offsets': {'from': 0, 'to': 1}}]}]}))
                return subprocess.CompletedProcess(command, 0, b'', b'')
            upgraded_model = Path(folder) / 'upgraded.bin'
            upgraded_model.touch()
            modes = [('es', True), ('fr', False), ('de', False), ('fr', True), ('de', True)]
            for language, installed in modes:
                model_path = upgraded_model if installed else Path(folder) / 'missing.bin'
                use_upgrade = installed and language in ('fr', 'de')
                with self.subTest(language=language, installed=installed), patch('live_subtitles.FRENCH_GERMAN_MODEL', model_path):
                    commands.clear()
                    clip_lengths.clear()
                    data = recognize(wav, Path(folder) / 'translated', run=run, language=language)
                    first_cues = [(34, 36, 'Hello world.')] if use_upgrade else [
                        (34, 34.9, 'Hello world.'), (35.1, 36, 'Hello world.')]
                    self.assertEqual(cues_from_whisper(data, 32), first_cues + [(39, 41, 'Hello world.')])
                    if use_upgrade:
                        frames = 40000 if language == 'fr' else 32000
                        self.assertEqual(clip_lengths, [frames, frames])
                    else:
                        self.assertEqual(clip_lengths, [14400, 14400, 32000])
                    for command in commands[1:]:
                        self.assertIn('--translate', command)
                        self.assertEqual(command[command.index('-l') + 1], language)
                        expected_model = upgraded_model if use_upgrade else MULTILINGUAL_MODEL
                        self.assertEqual(command[command.index('-m') + 1], str(expected_model))
                        self.assertEqual(command[command.index('-bs') + 1], '5' if use_upgrade else '1')
                        if use_upgrade:
                            self.assertEqual(command[command.index('-ac') + 1], '384')
                            self.assertIn('-oj', command)
                        else:
                            self.assertIn('-ojf', command)
            self.assertFalse(list(Path(folder).glob('*-speech-*')))

    def test_language_switch_replaces_captions_without_restarting_player(self):
        engine = menu_backend.Engine()
        engine.session = Mock(subtitle_source='whisper', caption_error='')
        engine.links = ['https://example.test/video', '', '', '']
        engine.file_loaded = True
        engine.settings.update(live_subtitles=True, caption_language='en', caption_delay=1.5)
        send = Mock()
        with patch.object(menu_backend, 'LiveSubtitles') as factory, patch.object(menu_backend, 'send'), patch.object(engine, 'prefetch_next'), patch('menu_requests.app.save_json') as save:
            for language in ('es', 'fr', 'de'):
                with self.subTest(language=language):
                    old = Mock(language=engine.settings['caption_language'])
                    engine.captions = old
                    engine.session.clear_captions.reset_mock()
                    request = {'action': 'settings', 'settings': {'caption_language': language}}
                    MenuRequest(request, engine, send).handle_settings()
                    self.assertEqual(save.call_args.args[1]['caption_language'], language)
                    self.assertEqual(send.call_args.args[0]['data']['caption_language'], language)
                    old.close.assert_called_once()
                    engine.session.clear_captions.assert_called_once()
                    self.assertEqual(factory.call_args.kwargs['options'].language, language)
                    self.assertEqual(factory.call_args.kwargs['options'].delay, 1.5)
            engine.session.load.assert_not_called()
            engine.session.close.assert_not_called()

    def test_missing_multilingual_model_reports_the_required_file(self):
        with patch('live_subtitles.MULTILINGUAL_MODEL', Path('/missing/ggml-base.bin')):
            with self.assertRaisesRegex(RuntimeError, 'ggml-base.bin'):
                LiveSubtitles(['video', '', '', ''], '/tmp', lambda _: None, lambda _: None, options=CaptionOptions(language='es'))


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
                                   options=CaptionOptions(position=1234, duration=2400))
            thread.return_value.start.assert_called_once()
            self.assertEqual(worker.position, 1234)
            self.assertEqual(worker.duration, 2400)

    def test_completion_keeps_published_cues_without_reloading_the_player(self):
        with tempfile.TemporaryDirectory() as folder, patch('live_subtitles.threading.Thread'), patch.object(Path, 'is_file', return_value=True):
            ready, status = Mock(), Mock()
            worker = LiveSubtitles(['video', '', '', ''], folder, ready, status)
            worker.post = lambda callback, value: callback(value)
            def transcribe(block):
                if block == 0:
                    worker.partial[block] = [(1, 2, 'Hello')]
                    worker.publish()
                    return worker.partial[block]
                worker.cancelled = True
                return []
            worker.transcribe = transcribe
            worker.work()
            ready.assert_called_once_with(str(worker.path))
            self.assertIn('Hello', worker.path.read_text())
            status.assert_called_with('Local English captions ready')
            self.assertEqual(worker.blocks[1], [])

    def test_worker_does_not_skip_dialogue_as_playback_advances(self):
        import threading
        from live_subtitles import CHUNK
        worker = LiveSubtitles.__new__(LiveSubtitles)
        worker.cancelled = False
        worker.language = 'auto'
        worker.condition = threading.Condition()
        worker.position = 10
        worker.duration = 200
        worker.blocks = {}
        worker.partial = {}
        worker.attempts = {}
        worker.post = Mock()
        worker.on_status = Mock()
        worker.publish = Mock()
        worker.publish_status = Mock()
        generated = []
        def transcribe(block):
            generated.append(block * CHUNK)
            worker.position += 2
            worker.cancelled = len(generated) == 3
            return []
        worker.transcribe = transcribe
        worker.work()
        self.assertEqual(generated, [8, 16, 24])
