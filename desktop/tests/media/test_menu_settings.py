import copy
import unittest
from unittest.mock import Mock, patch

import app
from menu_requests import dispatch


class SettingsTransactionTests(unittest.TestCase):
    def setUp(self):
        self.engine = Mock(settings=dict(app.DEFAULTS))
        self.before = copy.deepcopy(self.engine.settings)
        self.messages = []

    def request(self, settings):
        dispatch({'action': 'settings', 'request': 42, '_client': 'test-client',
                  'settings': settings}, self.engine, self.messages.append)

    def test_invalid_late_field_does_not_apply_earlier_settings(self):
        for delay in ['nan', 'inf', 'bad', None]:
            with self.subTest(delay=delay), patch.object(app, 'save_json') as save:
                self.request({'volume': 5, 'auto_next': False, 'caption_delay': delay})
                self.assertEqual(self.engine.settings, self.before)
                self.engine.settings_changed.assert_not_called()
                save.assert_not_called()
                self.assertEqual(self.messages[-1]['event'], 'error')
                self.assertEqual(self.messages[-1]['client'], 'test-client')

    def test_save_failure_preserves_settings_and_playback(self):
        with patch.object(app, 'save_json', side_effect=OSError('disk failure')):
            self.request({'volume': 5, 'caption_delay': 1})
        self.assertEqual(self.engine.settings, self.before)
        self.engine.settings_changed.assert_not_called()
        self.assertEqual(self.messages[-1]['event'], 'error')

    def test_non_object_settings_are_rejected_without_changes(self):
        with patch.object(app, 'save_json') as save:
            self.request(None)
        self.assertEqual(self.engine.settings, self.before)
        self.engine.settings_changed.assert_not_called()
        save.assert_not_called()
        self.assertEqual(self.messages[-1]['event'], 'error')

    def test_success_persists_before_publishing_settings(self):
        def save(path, settings):
            self.assertEqual(self.engine.settings, self.before)
            self.assertEqual(settings['volume'], 5)
        with patch.object(app, 'save_json', side_effect=save):
            self.request({'volume': 5, 'caption_delay': 1})
        self.assertEqual(self.engine.settings['volume'], 5)
        self.engine.settings_changed.assert_called_once()
        self.assertEqual(self.messages[-1]['event'], 'settings')
        self.assertEqual(self.messages[-1]['request'], 42)
