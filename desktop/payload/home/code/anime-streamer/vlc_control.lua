-- App-private interface for native VLC. Bound to loopback with a random password.
local json = require "dkjson"
local settings = config or {}
assert(tonumber(settings.port) and type(settings.password) == "string", "Missing private VLC control configuration")
local http = vlc.httpd("127.0.0.1", tonumber(settings.port))
local marker = ""
local channel = nil
local fullscreen_pending = false
local whisper_only = true

local function input_value(name, default)
    local input = vlc.object.input()
    if not input then return default end
    local ok, value = pcall(vlc.var.get, input, name)
    if ok and value ~= nil then return value end
    return default
end

local function status()
    local current = vlc.playlist.current()
    local item = vlc.playlist.get(current)
    local name = item and item.name or ""
    local subtitles = {}
    local audio_tracks = {}
    local chapter_count = 0
    local input = vlc.object.input()
    if input then
        if whisper_only then
            if input_value("spu-es", -1) ~= -1 then vlc.var.set(input, "spu-es", -1) end
            pcall(vlc.var.set, input, "secondary-spu-es", -1)
        end
        local values, labels = vlc.var.get_list(input, "spu-es")
        for i, id in ipairs(values or {}) do
            table.insert(subtitles, {id=id, name=(labels or {})[i] or tostring(id)})
        end
        local ok, chapters = pcall(vlc.var.get_list, input, "chapter")
        if ok and type(chapters) == "table" then chapter_count = #chapters end
        local ids, names = vlc.var.get_list(input, "audio-es")
        for i, id in ipairs(ids or {}) do table.insert(audio_tracks, {id=id, name=(names or {})[i] or tostring(id)}) end
    end
    return {state=vlc.playlist.status(), current=current, input=not not input,
        eof=marker ~= "" and name == marker, time=input_value("time", 0) / 1000000,
        duration=input_value("length", 0) / 1000000, sid=input_value("spu-es", -1),
        chapter=input_value("chapter", -1), chapter_count=chapter_count,
        input_state=input_value("state", 0), subtitles=subtitles,
        audio=input_value("audio-es", -1), audio_tracks=audio_tracks}
end

local function handle(_, query)
    -- Release temporary VLC object references before querying a new input.
    collectgarbage("collect")
    local args = {}
    for key, value in string.gmatch(query or "", "([^&=?]+)=([^&]*)") do
        args[vlc.strings.decode_uri(key)] = vlc.strings.decode_uri(value:gsub("+", " "))
    end
    local command = args.command
    local ok, error_text = pcall(function()
        if command == "load" then
            local data = json.decode(args.data or "{}")
            whisper_only = data.whisper_only ~= false
            fullscreen_pending = settings.fullscreen == true
            if channel then pcall(vlc.osd.channel_clear, channel) end
            channel = nil
            marker = "Media Browser EOF " .. tostring(data.generation)
            vlc.playlist.stop()
            vlc.playlist.clear()
            vlc.playlist.add({{path=data.url, name=data.title, options=data.options}})
            vlc.playlist.enqueue({{path="vlc://pause:86400", name=marker}})
        elseif command == "pause" then
            local state = vlc.playlist.status()
            if (args.value == "true" and state == "playing") or (args.value ~= "true" and state == "paused") then vlc.playlist.pause() end
        elseif command == "seek" then
            local input = vlc.object.input()
            if input then vlc.var.set(input, "time", math.floor(tonumber(args.value) * 1000000)) end
        elseif command == "stop" then
            marker = ""
            vlc.playlist.stop()
            vlc.playlist.clear()
        elseif command == "volume" then
            vlc.volume.set(math.floor(math.max(0, math.min(100, tonumber(args.value) or 80)) * 256 / 100))
        elseif command == "subtitle" then
            local input = vlc.object.input()
            if input and not whisper_only then vlc.var.set(input, "spu-es", tonumber(args.value)) end
        elseif command == "addsubtitle" then
            vlc.input.add_subtitle(args.value, args.select == "true")
        elseif command == "caption" then
            if vlc.object.vout() then
                if args.value and args.value ~= "" then
                    if not channel then channel = vlc.osd.channel_register() end
                    vlc.osd.channel_clear(channel)
                    vlc.osd.message(args.value, channel, "bottom", 2000000)
                elseif channel then vlc.osd.channel_clear(channel) end
            end
        elseif command == "clear-caption" then
            if channel and vlc.object.vout() then vlc.osd.channel_clear(channel) end
        elseif command == "quit" then
            marker = ""
            vlc.misc.quit()
        end
    end)
    local data = status()
    data.ok = ok
    if not ok then data.error = "VLC could not apply the player command." end
    local encoded = json.encode(data)
    collectgarbage("collect")
    return encoded
end

local endpoint = http:file("/session.json", "application/json", "", settings.password, handle, nil)
while endpoint do
    if fullscreen_pending then
        local vout = vlc.object.vout()
        if vout then
            local ok = pcall(vlc.var.set, vout, "fullscreen", true)
            if ok then fullscreen_pending = false end
        end
    end
    vlc.misc.mwait(vlc.misc.mdate() + 1000000)
end
