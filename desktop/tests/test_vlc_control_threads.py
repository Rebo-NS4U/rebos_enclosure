"""Keep VLC objects off the interface thread shared with HTTP callbacks."""
from pathlib import Path
import shutil
import subprocess
import unittest


class ControlThreadTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('lua5.1'), 'Lua 5.1 is required')
    def test_fullscreen_waits_for_callback_and_retries_until_vout_exists(self):
        script = Path(__file__).resolve().parents[2] / 'system/apps/media/vlc_control.lua'
        harness = r'''
local handler, callback, available, fullscreen = nil, false, false, 0
package.preload.dkjson = function() return {
 encode=function(data) return data end,
 decode=function() return {generation=1, url="test", title="Test"} end
} end
config={port=12345,password="test",fullscreen=true}
vlc={
 httpd=function() return {file=function(_,_,_,_,_,fn) handler=fn; return {} end} end,
 misc={mdate=function() error("Interface must return after HTTP setup") end,
       mwait=function() error("Interface must not race HTTP callbacks") end},
 object={input=function() return nil end, vout=function()
  assert(callback, "Interface thread must not acquire VLC objects")
  if available then return {} end
 end},
 playlist={stop=function() end,clear=function() end,add=function() end,enqueue=function() end,
 current=function() return 1 end,get=function() return {name="Test"} end,status=function() return "playing" end},
 strings={decode_uri=function(value) return value end},
 var={set=function(_,name,value) assert(callback and name=="fullscreen" and value); fullscreen=fullscreen+1 end}
}
dofile(arg[1])
assert(media_browser_http.host and media_browser_http.endpoint, "HTTP objects must stay rooted")
callback=true
assert(handler(nil,"command=load").ok)
assert(fullscreen==0)
available=true
assert(handler(nil,"").ok)
assert(fullscreen==1)
handler(nil,"")
assert(fullscreen==1, "Fullscreen must only apply once per load")
'''
        result = subprocess.run(['lua5.1', '-', str(script)], input=harness,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
