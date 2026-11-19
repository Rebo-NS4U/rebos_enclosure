"""Subtitle switching changes only captions and publishes the actual source."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'system/apps/media'))
from vlc_session import VlcSession
from menu_backend import Engine


class SubtitleSwitcherTests(unittest.TestCase):
    def session(self):
        session = object.__new__(VlcSession)
        session.loaded = session.requested = True
        session.finished = False
        session.subtitle_revision = 0
        session.pending_subtitle = None
        session.generation = 0
        session.provided_cues = [(i*5, i*5+3, f'I think you should come here now. What do we do? {i}') for i in range(30)]
        session.whisper_cues = [(0, 2, 'Generated English')]
        session.validate_provider = True
        session.subtitle_loading = False
        session.subtitle_source = 'provided'
        session.caption_error = ''
        session.caption_requested = True
        session.caption_text = 'Previous source'
        session.last_caption = 0
        session.last = {}
        session.last_state = {}
        session.live_enabled = True
        session.api = Mock()
        session.emit = Mock()
        session.cues = session.provided_cues
        session.cue_starts = [cue[0] for cue in session.cues]
        return session

    def test_switch_between_provider_whisper_and_off_without_reloading_video(self):
        session = self.session()
        for source, expected in [('whisper', session.whisper_cues), ('provided', session.provided_cues), ('off', [])]:
            session.apply(['subtitle-source', source])
            self.assertEqual(session.cues, expected)
            self.assertEqual(session.subtitle_tracks()['selected'], source)
            self.assertEqual(session.caption_requested, source != 'off')
        self.assertTrue(all(call.args[0] in ('clear-caption', 'subtitle') for call in session.api.call_args_list))

    def test_provider_is_preserved_when_generated_worker_stops_or_updates(self):
        session = self.session()
        original = list(session.provided_cues)
        session.apply(['captions-clear'])
        self.assertEqual(session.cues, original)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'generated.srt'
            path.write_text('1\n00:00:01,000 --> 00:00:03,000\nGenerated\n')
            session.apply(['captions-file', str(path)])
        self.assertEqual(session.cues, original)
        session.apply(['subtitle-source', 'whisper'])
        self.assertEqual(session.cues, [(1, 3, 'Generated')])

    def test_native_tracks_are_english_and_selection_disables_generated_osd(self):
        session = self.session()
        session.validate_provider = True
        session.last_state = {'sid': 2, 'subtitles': [{'id': 2, 'name': 'English'}, {'id': 3, 'name': 'Japanese'}]}
        choices = {row['id'] for row in session.subtitle_tracks()['options']}
        self.assertIn('native:2', choices)
        self.assertNotIn('native:3', choices)
        session.apply(['subtitle-source', 'native:2'])
        self.assertFalse(session.caption_requested)
        self.assertTrue(session.validate_provider)
        session.api.assert_called_with('subtitle', value=2)
        session.apply(['subtitle-source', 'whisper'])
        session.api.assert_called_with('subtitle', value=-1)

    def test_invalid_provider_timing_removes_option_and_falls_back(self):
        session = self.session()
        session.poll({'input': True, 'input_state': 3, 'state': 'playing', 'time': 1, 'duration': 1000})
        tracks = session.subtitle_tracks()
        self.assertEqual(tracks['selected'], 'whisper')
        self.assertNotIn('provided', {row['id'] for row in tracks['options']})
        session.emit.assert_any_call({'event':'property-change','name':'subtitle-tracks','data':tracks})

    def test_manual_whisper_selection_waits_for_player_and_rejects_invalid_tracks(self):
        engine = Mock()
        engine.session = self.session()
        engine.session.command = Mock()
        engine.file_loaded = True
        Engine.select_subtitles(engine, 'whisper')
        engine.session.command.assert_called_once_with(['subtitle-source', 'whisper'])
        engine.start_captions.assert_not_called()
        Engine.select_subtitles(engine, 'off')
        engine.start_captions.assert_not_called()
        with self.assertRaises(ValueError):
            Engine.select_subtitles(engine, 'native:99')

    def test_auto_transcription_starts_only_after_the_player_selects_fallback(self):
        engine = Mock(settings={'live_subtitles': True}, links=('video', '', '', ''), position=0, duration=100)
        engine.session = self.session()
        engine.session.show_captions = Mock()
        with patch('menu_backend.LiveSubtitles') as worker:
            for source in ('off', 'provided', 'native:2'):
                engine.session.subtitle_source = source
                Engine.start_captions(engine)
            worker.assert_not_called()
            engine.session.subtitle_source = 'whisper'
            Engine.start_captions(engine)
            worker.assert_called_once()
            engine.session.show_captions.assert_called_once()

    def test_vlc_keeps_an_explicit_native_track_and_off_disables_it(self):
        import shutil
        import subprocess
        if not shutil.which('lua5.1'):
            self.skipTest('Lua 5.1 is required')
        script = Path(__file__).resolve().parents[2] / 'system/apps/media/vlc_control.lua'
        harness = r'''
local handler
local sid = -1
package.preload.dkjson = function() return {encode=function(data) return data end} end
config = {port=12345, password="test"}
vlc = {
 httpd=function() return {file=function(_,_,_,_,_,callback) handler=callback end} end,
 object={input=function() return {} end, vout=function() return {} end},
 playlist={current=function() return 1 end, get=function() return {name="Video"} end,
           status=function() return "playing" end},
 strings={decode_uri=function(value) return value end},
 var={get=function(_,key) if key=="spu-es" then return sid end return 0 end,
      set=function(_,key,value) if key=="spu-es" then sid=value end end,
      get_list=function() return {-1,2}, {"Off","English"} end}
}
dofile(arg[1])
assert(handler(nil,"command=subtitle&value=2").sid==2)
assert(handler(nil,"").sid==2, "Status polling must preserve the selected track")
assert(handler(nil,"command=subtitle&value=-1").sid==-1)
assert(handler(nil,"").sid==-1)
'''
        result = subprocess.run(['lua5.1', '-', str(script)], input=harness, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_show_captions_preserves_explicit_off(self):
        session = self.session()
        session.select_subtitle_source('off')
        session.apply(['captions-show'])
        self.assertEqual(session.subtitle_source, 'off')
        self.assertFalse(session.caption_requested)
