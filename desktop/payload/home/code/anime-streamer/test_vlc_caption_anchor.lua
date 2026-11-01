-- Run with lua5.1 test_vlc_caption_anchor.lua from this directory.
-- A native subtitle arriving late must not overlap Whisper OSD.
local handler
local tracks, labels = {-1, 2}, {"Disable", "English"}
local selected = 2
local now = 0
package.preload.dkjson = function() return {encode=function(data) return data end} end
config = {port=12345, password="test"}
vlc = {
    misc={mdate=function() return now end},
    httpd=function() return {file=function(_, _, _, _, _, callback)
        handler = callback
        return nil
    end} end,
    object={input=function() return {} end},
    playlist={current=function() return 1 end, get=function() return {name="Video"} end,
              status=function() return "playing" end},
    strings={decode_uri=function(value) return value end},
    var={
        get=function(_, name)
            if name == "spu-es" then return selected end
            if name == "sub-description" then return "" end
            return 0
        end,
        get_list=function(_, name)
            if name == "spu-es" then return tracks, labels end
            return {}, {}
        end,
        create=function() end, set=function(_, name, value)
            if name == "spu-es" then selected = value end
        end
    },
    input={add_subtitle=function() end}
}
dofile("vlc_control.lua")
assert(handler(nil, "").sid == -1, "Native subtitle must be disabled")
selected = 32
assert(handler(nil, "").sid == -1, "Late native track must be disabled")
print("PASS: native subtitles cannot overlap Whisper OSD")
