import unittest
from unittest.mock import Mock, call, patch

import menu_backend
from menu_requests import dispatch


class SeekPreviewTests(unittest.TestCase):
    def setUp(self):
        self.engine = menu_backend.Engine.__new__(menu_backend.Engine)
        self.engine.file_loaded = True
        self.engine.session = Mock()
        self.engine.position = 62
        self.engine.duration = 100
        self.clock = self.enterContext(patch.object(menu_backend.time, 'monotonic', return_value=10))
        self.timer = self.enterContext(patch.object(menu_backend.GLib, 'timeout_add'))
        self.send = self.enterContext(patch.object(menu_backend, 'send'))

    def test_repeated_skips_show_requested_time_before_playback_moves(self):
        dispatch({'action': 'skip', 'direction': 'forward'}, self.engine, self.send)
        old_callback = self.timer.call_args.args[1]
        dispatch({'action': 'skip', 'direction': 'forward'}, self.engine, self.send)
        callback = self.timer.call_args.args[1]
        self.assertEqual(self.send.call_args_list, [
            call(dict(event='seek-preview', available=True, target=72)),
            call(dict(event='seek-preview', available=True, target=82)),
        ])
        self.assertEqual(self.engine.session.command.call_args_list, [call(['seek', 72]), call(['seek', 82])])
        self.assertFalse(old_callback())
        self.clock.return_value = 14
        self.assertTrue(callback())
        self.engine.position = 82
        self.assertFalse(callback())
        self.send.assert_called_with(dict(event='seek-preview', available=True, target=None))

    def test_back_skip_clamps_and_stop_clears_preview(self):
        self.engine.position = 3
        dispatch({'action': 'skip', 'direction': 'back'}, self.engine, self.send)
        self.engine.session.command.assert_called_once_with(['seek', 0])
        menu_backend.Engine.reset_seek_preview(self.engine)
        self.assertFalse(self.timer.call_args.args[1]())
        self.send.assert_called_with(dict(event='seek-preview', available=False, target=None))
