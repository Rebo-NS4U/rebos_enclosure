"""Validate preset consistency, DSP headroom and private settings without hardware."""
import ast
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'system/apps/shell/scripts'))
from audio_eq_dsp import PRESETS, FREQUENCIES, validate_gains, headroom, response_db, graph
from audio_equalizer import Equalizer


class EqualizerTests(unittest.TestCase):
    def test_ui_presets_match_backend(self):
        source = (ROOT / 'system/apps/shell/modules/services/AudioEqualizer.qml').read_text()
        block = re.search(r'property var presets: (\(\{.*?\}\))', source, re.S)
        self.assertEqual(ast.literal_eval(block[1]), PRESETS)

    def test_rejects_malformed_and_non_finite_bands(self):
        for values in ([], [0]*9, [0]*11, [13]*10, [-13]*10, [True]*10, [float('nan')]*10, [float('inf')]*10):
            with self.assertRaises(ValueError):
                validate_gains(values)
        self.assertEqual(validate_gains([1.234]*10), [1.2]*10)

    def test_presets_have_compensated_frequency_response(self):
        for name, gains in PRESETS.items():
            with self.subTest(preset=name):
                compensation = headroom(gains)
                for frequency in [20*(23900/20)**(i/2047) for i in range(2048)]:
                    self.assertLessEqual(response_db(gains, frequency) + compensation, .01)
        self.assertAlmostEqual(headroom(PRESETS['Flat']), 0)
        self.assertGreater(response_db(PRESETS['Speech'], 2000), response_db(PRESETS['Speech'], 63))
        self.assertGreater(response_db(PRESETS['Bass'], 63), response_db(PRESETS['Bass'], 4000))

    def test_graph_has_ten_live_controls_and_safe_routing(self):
        config = graph(PRESETS['Music'], 'fixture_speaker')
        args = config['context.modules'][-1]['args']
        self.assertEqual(args['playback.props']['target.object'], 'fixture_speaker')
        nodes = args['filter.graph']['nodes']
        self.assertEqual([n['control']['Freq'] for n in nodes[1:]], list(FREQUENCIES))
        self.assertLessEqual(nodes[0]['control']['Mult'], 1)
        self.assertEqual(len(args['filter.graph']['links']), 10)

    def test_saved_settings_default_to_bypass_and_restore(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, XDG_CONFIG_HOME=folder):
            eq = Equalizer()
            self.assertFalse(eq.settings['enabled'])
            eq.configure({'enabled':True, 'gains':PRESETS['Movies'], 'preset':'Movies'})
            restored = Equalizer()
            self.assertEqual(restored.settings, eq.settings)
            self.assertEqual(restored.path.stat().st_mode & 0o777, 0o600)
            restored.configure({'enabled':False})
            self.assertEqual(restored.settings['preset'], 'Movies')
            restored.path.write_text('{broken')
            self.assertFalse(Equalizer().settings['enabled'])

    def test_backend_failure_preserves_intent_for_reconnect(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, XDG_CONFIG_HOME=folder):
            eq = Equalizer()
            eq.configure({'enabled':True})
            with patch.object(eq, 'reconcile', side_effect=RuntimeError('Audio disconnected')), patch.object(eq, 'stop') as stop:
                eq.tick()
                stop.assert_called_once()
            self.assertEqual(eq.error, 'Audio disconnected')
            self.assertTrue(eq.settings['enabled'])


if __name__ == '__main__':
    unittest.main()
