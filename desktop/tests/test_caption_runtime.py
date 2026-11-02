"""Validate runtime selection and reversible activation without GPU access."""
from pathlib import Path
import sys
import tempfile
import unittest
import wave

MEDIA = Path(__file__).resolve().parents[1] / 'payload/home/code/anime-streamer'
sys.path.insert(0, str(MEDIA))
from whisper_runtime import command
from caption_runtime_setup import activate


class CaptionRuntimeTests(unittest.TestCase):
    def test_short_clip_uses_bounded_context_and_gpu_when_available(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            gpu = root / 'build-vulkan/bin/whisper-cli'
            gpu.parent.mkdir(parents=True)
            gpu.write_text('#!/bin/sh\nexit 0\n')
            gpu.chmod(0o755)
            wav = root / 'speech.wav'
            with wave.open(str(wav), 'wb') as audio:
                audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\0' * 16000 * 2 * 4)
            args = command(['-ng', '-f', str(wav), '-l', 'auto', '--translate'], root)
            self.assertEqual(args[0], str(gpu))
            self.assertNotIn('-ng', args)
            self.assertIn('--translate', args)
            self.assertEqual(args[args.index('-ac') + 1], '256')
            # An explicit context preference is retained.
            args = command(['-f', str(wav), '-ac', '512'], root)
            self.assertEqual(args.count('-ac'), 1)
            self.assertEqual(args[-1], '512')

    def test_cpu_fallback_keeps_no_gpu_option(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = command(['-ng', '--help'], root)
            self.assertEqual(args, [str(root / 'build/bin/whisper-cli-cpu'), '-ng', '--help'])

    def test_activation_preserves_cpu_binary_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cli = root / 'build/bin/whisper-cli'
            cli.parent.mkdir(parents=True)
            original = b'\x7fELFcpu-fallback'
            cli.write_bytes(original)
            cli.chmod(0o755)
            activate(root)
            activate(root)
            self.assertEqual(cli.with_name('whisper-cli-cpu').read_bytes(), original)
            self.assertEqual(cli.read_bytes(), (MEDIA / 'whisper_runtime.py').read_bytes())
            self.assertTrue(cli.stat().st_mode & 0o111)

    def test_activation_refuses_to_overwrite_unknown_entrypoint(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cli = root / 'build/bin/whisper-cli'
            cli.parent.mkdir(parents=True)
            cli.write_text('custom launcher')
            with self.assertRaisesRegex(RuntimeError, 'Unknown'):
                activate(root)
            self.assertEqual(cli.read_text(), 'custom launcher')
