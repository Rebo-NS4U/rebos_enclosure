"""Keep the caption channel alive without input or window interaction."""
from pathlib import Path
import shutil
import subprocess
import unittest


class IdleCaptionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('lua5.1'), 'Lua 5.1 is required')
    def test_refresh_does_not_clear_or_fade_caption_and_end_clears_it(self):
        script = Path(__file__).resolve().parents[1] / 'payload/home/code/anime-streamer/vlc_control.lua'
        harness = r'''
local handler
local registrations, clears, messages = 0, 0, {}
package.preload.dkjson = function() return {encode=function(data) return data end} end
config = {port=12345, password="test"}
vlc = {
 httpd=function() return {file=function(_, _, _, _, _, callback) handler=callback end} end,
 object={input=function() return {} end, vout=function() return {} end},
 playlist={current=function() return 1 end, get=function() return {name="Video"} end,
           status=function() return "playing" end},
 strings={decode_uri=function(value) return value end},
 var={get=function() return 0 end, set=function() end,
      get_list=function() return {}, {} end},
 osd={channel_register=function() registrations=registrations+1; return 17 end,
      channel_clear=function(id) assert(id==17); clears=clears+1 end,
      message=function(text,id,position,duration)
          table.insert(messages,{text=text,id=id,position=position,duration=duration})
      end}
}
dofile(arg[1])
-- Heartbeats arrive without any mouse, focus, resize or keyboard event.
for second=1,15 do
 assert(handler(nil,"command=caption&value=Dialogue").ok ~= false)
end
assert(registrations==1, "Caption refresh must reuse one channel")
assert(clears==0, "Refreshing must not clear a still-active caption")
assert(#messages==15)
for _,message in ipairs(messages) do
 assert(message.duration>=10000000, "Caption must not enter VLC's short OSD fade window")
 assert(message.id==17 and message.position=="bottom")
end
handler(nil,"command=clear-caption")
assert(clears==1, "Cue end must clear the caption immediately")
'''
        result = subprocess.run(['lua5.1', '-', str(script)], input=harness,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
