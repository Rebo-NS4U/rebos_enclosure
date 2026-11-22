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

    def test_skip_intro_is_offered_only_during_labeled_chapters_with_a_destination(self):
        self.engine.chapter = 1
        self.engine.chapter_name = 'Opening Credits'
        self.engine.next_chapter = 2
        self.engine.history = {}
        self.engine.captions = None
        self.engine.save_progress = Mock()
        self.engine.settings_changed = Mock()
        context = ({'id': 'show'}, ['1'], 0, 1)
        opening = {'index': 1, 'name': 'Opening Credits', 'next': 2}
        event = {'name': 'chapter-info', 'data': opening}
        self.engine._event_properties(event, 1, context)
        self.send.assert_called_once_with(dict(event='skip-intro', available=True))
        dispatch({'action': 'skip_intro'}, self.engine, self.send)
        self.engine.session.command.assert_called_once_with(['skip-intro', 1])

        for chapter in ({'index': 2, 'name': 'Episode', 'next': 3},
                        {'index': 3, 'name': 'Intro', 'next': None}):
            self.engine._event_properties(dict(event, data=chapter), 1, context)
            dispatch({'action': 'skip_intro'}, self.engine, self.send)
        self.send.assert_called_with(dict(event='skip-intro', available=False))
        self.engine.session.command.assert_called_once()

        self.engine._event_properties(event, 1, context)
        self.engine.reset_seek_preview()
        dispatch({'action': 'skip_intro'}, self.engine, self.send)
        self.assertFalse(self.engine.intro_offered)
        self.engine.session.command.assert_called_once()
