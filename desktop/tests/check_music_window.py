#!/usr/bin/env python3
"""Music UI acceptance in a private Niri/Xvfb session; uses silent fixture audio.

Run: python3 desktop/tests/check_music_window.py
Saves /tmp/enclosure-music-acceptance.png; never uses the real desktop/library.
"""
import importlib.util
import sys
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
source = ROOT/"system/apps/shell"

def session():
    with tempfile.TemporaryDirectory(prefix='enclosure-music-check-') as directory:
        root = Path(directory)
        home = root/'home'
        (home/'Music').mkdir(parents=True)
        config = root/'shell'
        config.mkdir()
        for name in ('modules','config','scripts','assets','version'):
            (config/name).symlink_to(source/name, target_is_directory=True)
        audio_bin = root/'audio-bin'
        audio_bin.mkdir()
        # Give the real spectrum reader a deterministic music stream in the private session.
        (audio_bin/'pactl').write_text(r"""#!/bin/sh
case "$4" in
  sink-inputs) printf '%s\n' '[{"index":1,"sink":7,"properties":{"media.role":"music"}}]' ;;
  sinks) printf '%s\n' '[{"index":7,"monitor_source_name":"test.monitor"}]' ;;
esac
""")
        (audio_bin/'parec').write_text(
            '#!/usr/bin/env python3\n'
            'import math, struct, sys, time\n'
            'frame = struct.pack("<1000h", *(int(18000 * math.sin(2 * math.pi * i / 200)) for i in range(1000)))\n'
            'while True:\n'
            '    sys.stdout.buffer.write(frame)\n'
            '    sys.stdout.buffer.flush()\n'
            '    time.sleep(1000 / 24000)\n')
        for command in audio_bin.iterdir():
            command.chmod(0o755)
        for index in range(2):
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','anullsrc=r=44100:cl=stereo',
                '-t','4','-metadata',f'title=Acceptance song {index+1}','-metadata','artist=Enclosure',
                '-metadata','album=Music acceptance',str(home/'Music'/f'{index}.flac')],check=True)
        (home/'Music/0.lrc').write_text('[00:00.00]First line\n[00:01.00]Second line')
        (home/'Music/1.lrc').write_text('I kept all of your letters in a drawer Now the memories are fading away\nThird untimed line\nLast untimed line')
        qml = '''//@ pragma UseQApplication
    import QtQuick
    import QtTest
    import Quickshell
    import Quickshell.Services.Mpris
    import qs.modules.widgets.music
    import qs.modules.globals
    import qs.modules.services
    ShellRoot {
        TestCase { id: input; when: false }
        MusicWindow {
            id: music
            property string requestedPreview: ""
            function previewSuggestion(uri) { requestedPreview = uri; }
        }
        QtObject {
            id: spotify
            property string dbusName: "org.mpris.MediaPlayer2.spotify"
            property string trackTitle: "Suggested song"
            property string trackArtists: "Suggested artist"
            property string trackAlbum: "Spotify suggestions"
            property string trackArtUrl: ""
            property var metadata: ({"xesam:url":"spotify:track:" + "z".repeat(22)})
            property real length: 180
            property real position: 30
            property bool isPlaying: true
            property bool canTogglePlaying: true
            property bool canPlay: true
            property bool canPause: true
            property bool canGoNext: true
            property bool canGoPrevious: true
            property bool canSeek: true
            property bool shuffleSupported: true
            property bool loopSupported: true
            property bool volumeSupported: true
            property bool shuffle: false
            property int loopState: 0
            property real volume: 0.6
            property int nextCalls: 0
            property int previousCalls: 0
            function togglePlaying() { isPlaying = !isPlaying; }
            function pause() { isPlaying = false; }
            function play() { isPlaying = true; }
            function stop() { isPlaying = false; }
            function next() { nextCalls++; }
            function previous() { previousCalls++; }
        }
        function findItem(item, name) {
            if (item.objectName === name) return item;
            for (const child of item.children) { const found = findItem(child, name); if (found) return found; }
            return null;
        }
        function tabTo(item) {
            for (let i = 0; item && !item.activeFocus && i < 24; i++) input.keyClick(Qt.Key_Tab);
            return item?.activeFocus;
        }
        Component.onCompleted: GlobalStates.musicWindowVisible = true
        Timer {
            property int attempts: 0
            property int phase: 0
            property int repeatStart: 0
            property bool checkedShortPlaylist: false
            interval: 200; running: true; repeat: true
            onTriggered: {
                attempts++;
                if (attempts > 90) { console.error("MUSIC_ACCEPTANCE_TIMEOUT", phase, music.notice); Qt.exit(1); }
                if (phase === 0 && !music.busy && music.tracks.length === 2) {
                    const backdrop = findItem(music.contentItem, "music-background");
                    if (music.color.a !== 0 || !backdrop || backdrop.variant !== "bg") { console.error("MUSIC_SHARED_BACKGROUND_FAILED"); Qt.exit(1); }
                    if (music.repeatMode !== "Playlist") { console.error("MUSIC_REPEAT_DEFAULT_FAILED"); Qt.exit(1); }
                    const favorite = findItem(music.contentItem, "music-favorite-current");
                    if (!favorite || favorite.enabled) { console.error("MUSIC_FAVORITE_EMPTY_FAILED"); Qt.exit(1); }
                    const repeat = findItem(music.contentItem, "music-repeat");
                    repeat.clicked();
                    if (music.repeatMode !== "Track" || repeat.text !== "Repeat song") { console.error("MUSIC_REPEAT_TRACK_FAILED"); Qt.exit(1); }
                    repeat.clicked();
                    if (music.repeatMode !== "None" || repeat.checked) { console.error("MUSIC_REPEAT_OFF_FAILED"); Qt.exit(1); }
                    repeat.clicked();
                    if (music.repeatMode !== "Playlist" || repeat.text !== "Repeat all") { console.error("MUSIC_REPEAT_ALL_FAILED"); Qt.exit(1); }
                    const previousPlaylists = music.playlists;
                    music.playlists = [
                        {id: "manual", name: "My playlist", paths: [music.tracks[1].path]},
                        {id: "mix", name: "Enclosure Mix", sourceName: "Daily Mix 1", mix: true, paths: [music.tracks[0].path]}
                    ];
                    for (const removed of ["Home", "Previews", "Downloaded Mixes"]) {
                        if (findItem(music.contentItem, "music-navigation-" + removed)) { console.error("REDUNDANT_MUSIC_TAB"); Qt.exit(1); }
                    }
                    const mode = findItem(music.contentItem, "music-preview-mode");
                    const mixesPane = findItem(music.contentItem, "music-daily-mixes");
                    mode.clicked();
                    if (!mixesPane.previewOnly || mixesPane.section !== "imported") { console.error("PREVIEW_MODE_FAILED"); Qt.exit(1); }
                    mode.clicked();
                    if (mixesPane.previewOnly || mixesPane.section !== "current") { console.error("BROWSE_MODE_FAILED"); Qt.exit(1); }
                    const downloadedTab = findItem(music.contentItem, "music-navigation-Playlists");
                    if (!downloadedTab) { console.error("DOWNLOADED_MIX_NAV_MISSING"); Qt.exit(1); }
                    downloadedTab.clicked();
                    if (music.page !== "Playlists" || music.playlists.length !== 2 || music.shownTracks.length !== 2 || music.cardTracks(music.page, "mix")[0].path !== music.tracks[0].path) { console.error("DOWNLOADED_MIX_SECTION_FAILED"); Qt.exit(1); }
                    music.playlists = previousPlaylists;
                    music.navigate("Albums");
                    music.volume = 0;
                    const largeQueue = Array.from({length: 150}, (_, i) => Object.assign({}, music.tracks[i % 2], {title: "Queue song " + i}));
                    music.play(largeQueue, 0);
                    if (music.queue.length !== 150 || music.currentIndex !== 0 || music.notice !== "" ||
                        music.nextQueueTrack?.title !== "Queue song 1") { console.error("MUSIC_LARGE_QUEUE_FAILED"); Qt.exit(1); return; }
                    const firstQueued = music.queue[0];
                    music.enqueue(music.tracks[0]);
                    if (music.queue.length !== 151 || music.queue[0] !== firstQueued || music.notice !== "") { console.error("MUSIC_LARGE_QUEUE_APPEND_FAILED"); Qt.exit(1); return; }
                    music.shuffle = true;
                    const shuffledNext = music.nextQueueTrack;
                    music.next();
                    if (shuffledNext === firstQueued || music.current !== shuffledNext) { console.error("MUSIC_SHUFFLE_PREDICTION_FAILED"); Qt.exit(1); return; }
                    music.shuffle = false;
                    music.play(largeQueue, 149);
                    if (music.queue.length !== 150 || music.currentIndex !== 149 || music.current.title !== "Queue song 149" ||
                        music.nextQueueTrack?.title !== "Queue song 0" || music.notice !== "") { console.error("MUSIC_LARGE_QUEUE_SELECTED_FAILED"); Qt.exit(1); return; }
                    music.repeatMode = "None";
                    if (music.nextQueueTrack || music.canNext) { console.error("MUSIC_END_OF_QUEUE_FAILED"); Qt.exit(1); return; }
                    music.repeatMode = "Playlist";
                    music.play(music.tracks.slice(0, 1), 0);
                    music.enqueue(music.tracks[1]);
                    if (music.queue.length !== 2 || music.queue[1].path !== music.tracks[1].path) { console.error("MUSIC_QUEUE_APPEND_FAILED"); Qt.exit(1); }
                    const playCard = findItem(music.contentItem, "music-card-play");
                    if (!playCard) return;
                    playCard.clicked();
                    if (music.currentIndex < 0 || music.currentIndex >= music.queue.length) { console.error("MUSIC_RANDOM_START_FAILED"); Qt.exit(1); }
                    music.play(music.queue, 0);
                    if (music.currentIndex !== 0) { console.error("MUSIC_EXPLICIT_START_FAILED"); Qt.exit(1); }
                    music.shuffle = true;
                    music.next(false);
                    if (music.currentIndex !== 1 || !music.canPreviousLocal) { console.error("MUSIC_SHUFFLE_NEXT_FAILED"); Qt.exit(1); return; }
                    music.previous();
                    if (music.currentIndex !== 0 || music.canPreviousLocal) { console.error("MUSIC_SHUFFLE_PREVIOUS_FAILED"); Qt.exit(1); return; }
                    music.next(false);
                    if (music.currentIndex !== 1 || music.shuffleHistory.length !== 2) { console.error("MUSIC_SHUFFLE_RETRACE_FAILED"); Qt.exit(1); return; }
                    music.shuffle = false;
                    music.play(music.queue, 0);
                    if (music.page !== "Albums" || music.queue.length !== 2) { console.error("MUSIC_CARD_PLAY_FAILED"); Qt.exit(1); }
                    phase = 1;
                } else if (phase === 1 && music.playing) {
                    if (music.lyricLines.length !== 2 || music.estimatedTiming) { console.error("MUSIC_LYRICS_FAILED"); Qt.exit(1); }
                    music.seek(1200);
                    const favorite = findItem(music.contentItem, "music-favorite-current");
                    if (favorite.parent.children[0].text !== music.current.title) { console.error("MUSIC_FAVORITE_PLACEMENT_FAILED"); Qt.exit(1); }
                    favorite.clicked();
                    if (!favorite.checked || !music.favorites.includes(music.current.path)) { console.error("MUSIC_FAVORITE_ADD_FAILED"); Qt.exit(1); }
                    favorite.clicked();
                    if (favorite.checked || music.favorites.includes(music.current.path)) { console.error("MUSIC_FAVORITE_REMOVE_FAILED"); Qt.exit(1); }
                    favorite.clicked();
                    music.playlists = [
                        {id:"test",name:"Acceptance",paths:music.queue.map(t=>t.path).reverse()},
                        {id:"regular-add",name:"Regular add",paths:[]},
                        {id:"fullscreen-add",name:"Fullscreen add",paths:[]}
                    ];
                    music.save();
                    const add = findItem(music.contentItem, "music-add-current-to-playlist");
                    input.mouseClick(add, add.width / 2, add.height / 2);
                    phase = 12;
                } else if (phase === 12) {
                    const choices = findItem(music.contentItem, "music-playlist-choices");
                    if (!choices?.itemAtIndex(1)) return;
                    if (choices.itemAtIndex(0).enabled) { console.error("MUSIC_PLAYLIST_DUPLICATE_ENABLED"); Qt.exit(1); return; }
                    const choice = choices.itemAtIndex(1);
                    input.mouseClick(choice, choice.width / 2, choice.height / 2);
                    phase = 13;
                } else if (phase === 13 && !music.busy) {
                    if (music.playlists[1].paths[0] !== music.tracks[0].path) { console.error("MUSIC_REGULAR_PLAYLIST_ADD_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Escape);
                    if (!music.visible || findItem(music.contentItem, "music-playlist-choices")?.visible) { console.error("MUSIC_PLAYLIST_PICKER_ESCAPE_FAILED"); Qt.exit(1); return; }
                    findItem(music.contentItem, "music-repeat").clicked();
                    if (music.repeatMode !== "Track") { console.error("MUSIC_REPEAT_TOGGLE_FAILED"); Qt.exit(1); }
                    music.seek(3800);
                    repeatStart = attempts;
                    phase = 10;
                } else if (phase === 10 && attempts >= repeatStart + 4) {
                    if (!music.playing || music.currentIndex !== 0 || music.lyricIndex !== 0) { console.error("MUSIC_REPEAT_SONG_FAILED"); Qt.exit(1); }
                    music.next(false);
                    phase = 2;
                } else if (phase === 2 && music.currentIndex === 1 && music.playing) {
                    findItem(music.contentItem, "music-repeat").clicked();
                    if (music.repeatMode !== "None") { console.error("MUSIC_REPEAT_DISABLE_FAILED"); Qt.exit(1); }
                    music.control({action:"Pause"});
                    music.side = "Lyrics";
                    if (!music.estimatedTiming || music.lyricLines.length !== 4) { console.error("MUSIC_ESTIMATES_FAILED"); Qt.exit(1); }
                    if (music.lyricLines[1].text !== "Now the memories are fading away") { console.error("MUSIC_JOINED_LINES_FAILED"); Qt.exit(1); }
                    music.seek(2200);
                    if (music.lyricIndex !== 2) { console.error("MUSIC_ESTIMATE_SEEK_FAILED"); Qt.exit(1); }
                    music.navigate("Albums");
                    phase = 3;
                } else if (phase === 3 && !music.playing) {
                    if (music.lyricIndex !== 2) { console.error("MUSIC_ESTIMATE_PAUSE_FAILED"); Qt.exit(1); }
                    music.seek(0);
                    if (music.lyricIndex !== 0) { console.error("MUSIC_ESTIMATE_REWIND_FAILED"); Qt.exit(1); }
                    music.navigate("Playlists");
                    phase = 4;
                } else if (phase === 4) {
                    const playCard = findItem(music.contentItem, "music-card-play");
                    if (!playCard) return;
                    playCard.clicked();
                    if (music.currentIndex < 0 || music.currentIndex >= music.queue.length) { console.error("MUSIC_RANDOM_START_FAILED"); Qt.exit(1); }
                    music.play(music.queue, 0);
                    if (music.currentIndex !== 0) { console.error("MUSIC_EXPLICIT_START_FAILED"); Qt.exit(1); }
                    if (music.page !== "Playlists" || music.queue[0].path !== music.tracks[1].path) { console.error("MUSIC_PLAYLIST_CARD_FAILED"); Qt.exit(1); }
                    music.control({action:"Pause"});
                    music.navigate("Playlist", "regular-add");
                    phase = 98;
                } else if (phase === 98 && !music.busy) {
                    const row = findItem(music.contentItem, "music-track-row-0");
                    const remove = row && findItem(row, "music-track-remove-0");
                    if (!remove?.visible) return;
                    const requestId = music.requestId;
                    input.mouseClick(remove, remove.width / 2, remove.height / 2);
                    if (remove.text !== "Confirm remove" || music.requestId !== requestId || music.shownTracks.length !== 1) { console.error("MUSIC_REMOVE_FIRST_CLICK_FAILED"); Qt.exit(1); return; }
                    phase = 980;
                } else if (phase === 980) {
                    const row = findItem(music.contentItem, "music-track-row-0");
                    const remove = findItem(row, "music-track-remove-0");
                    input.mouseClick(remove, remove.width / 2, remove.height / 2);
                    phase = 99;
                } else if (phase === 99 && !music.busy) {
                    if (music.shownTracks.length !== 0 || music.tracks.length !== 2) { console.error("MUSIC_REMOVE_SECOND_CLICK_FAILED"); Qt.exit(1); return; }
                    console.log("MUSIC_REMOVE_CONFIRMATION_PASSED");
                    music.navigate("Playlist", "test");
                    phase = 40;
                } else if (phase === 40) {
                    const row = findItem(music.contentItem, "music-track-row-0");
                    if (!row || row.width < 100) return;
                    input.mouseClick(row, row.width * 0.45, row.height / 2);
                    phase = 41;
                } else if (phase === 41 && music.playing) {
                    if (music.current.path !== music.playlists[0].paths[0]) { console.error("MUSIC_ROW_CLICK_WRONG_TRACK"); Qt.exit(1); }
                    const queue = findItem(music.contentItem, "music-track-queue-0");
                    const length = music.queue.length;
                    input.mouseClick(queue, queue.width / 2, queue.height / 2);
                    if (music.queue.length !== length + 1 || !music.playing) { console.error("MUSIC_ROW_QUEUE_CLICK_FAILED"); Qt.exit(1); }
                    console.log("MUSIC_FULL_ROW_CLICK_PASSED");
                    music.control({action:"Pause"});
                    music.navigate("Downloads");
                    const downloads = findItem(music.contentItem, "music-downloads");
                    const start = findItem(music.contentItem, "music-download-start");
                    if (!downloads || start.enabled) { console.error("MUSIC_DOWNLOAD_EMPTY_LINKS_FAILED"); Qt.exit(1); }
                    const links = findItem(music.contentItem, "music-download-links");
                    links.text = "https://open.spotify.com/track/example";
                    if (!downloads.canDownload) { console.error("MUSIC_DOWNLOAD_LINKS_FAILED"); Qt.exit(1); }
                    links.text = "";
                    if (downloads.canDownload) { console.error("MUSIC_DOWNLOAD_EMPTY_LINKS_FAILED"); Qt.exit(1); }
                    const mixes = findItem(music.contentItem, "music-daily-mixes");
                    const mixDownloads = findItem(music.contentItem, "music-downloads");
                    const local = Object.assign({}, music.tracks[0], {spotifyUri: "spotify:track:" + "b".repeat(22)});
                    music.tracks = [local, music.tracks[1]];
                    mixes.selected = {name: "Daily Mix 1", tracks: [
                        {uri: local.spotifyUri, title: local.title},
                        {uri: "spotify:track:" + "c".repeat(22), title: "Not downloaded"}]};
                    if (mixes.previewTracks.length !== 2 || mixes.playableTracks.length !== 1) { console.error("MIX_PREVIEW_MATCH_FAILED"); Qt.exit(1); }
                    mixes.playRequested(mixes.playableTracks, 0);
                    if (music.current.path !== local.path || music.queue.length !== 1) { console.error("MIX_PREVIEW_PLAY_FAILED"); Qt.exit(1); }
                    if (!mixDownloads.prepareMix({links: "https://open.spotify.com/track/" + "b".repeat(22), folder: "/tmp/mix-preview-fixture"}) || !mixDownloads.mixTracks) { console.error("MIX_DOWNLOAD_PREPARE_FAILED"); Qt.exit(1); }
                    music.navigate("Spotify playlists");

                    repeatStart = attempts; phase = 5;
                } else if (phase === 5 && attempts >= repeatStart + 3) {
                    const mixes = findItem(music.contentItem, "music-daily-mixes");
                    mixes.mixes = {current: [{name: "Daily Mix 1 with a very long playlist title that wraps safely across the available width", tracks: mixes.selected.tracks}], saved: [{name: "Daily Mix 1 saved snapshot with a long title", tracks: mixes.selected.tracks, savedAt: "2026-11-16T12:00:00Z"}], checked: ""};
                    music.minimumWidth=1160; music.width=1240; repeatStart = attempts; phase = 6;
                } else if (phase === 6 && attempts >= repeatStart + 3) {
                    const mixes = findItem(music.contentItem, "music-daily-mixes");
                    const label = findItem(music.contentItem, "music-mix-label");
                    const preview = findItem(music.contentItem, "music-mix-preview");
                    const nav = findItem(music.contentItem, "music-top-navigation");
                    const tabs = findItem(music.contentItem, "music-navigation-tabs");
                    if (!label || label.width > mixes.width || !preview || preview.height <= 100 || !nav || !tabs || nav.width < music.width - 40) { console.error("MIX_LAYOUT_FAILED"); Qt.exit(1); return; }
                    const navButton = findItem(music.contentItem,"music-navigation-Songs");
                    const lastTab=findItem(music.contentItem,"music-navigation-Now playing");
                    if (Math.abs(lastTab.x + lastTab.width - tabs.width) > 1) { console.error("MUSIC_TOP_NAV_FILL_FAILED"); Qt.exit(1); return; }
                    navButton.clicked();
                    if (music.page !== "Songs") { console.error("MUSIC_TOP_NAV_FAILED"); Qt.exit(1); return; }
                    music.navigate("Spotify playlists");
                    const savedTab = findItem(music.contentItem,"music-mixes-saved"); savedTab.clicked();
                    if (mixes.section !== "saved" || mixes.displayedMixes.length !== 1) { console.error("MIX_SAVED_NAV_FAILED"); Qt.exit(1); return; }
                    findItem(music.contentItem,"music-mixes-current").clicked();
                    const grid = findItem(music.contentItem,"music-mix-grid");
                    if (!mixes.wide || !grid.visible || !preview.visible || grid.width + preview.width > mixes.width) { console.error("MIX_WIDE_LAYOUT_FAILED",mixes.width,mixes.wide,grid.visible,preview.visible,grid.width,preview.width); Qt.exit(1); return; }
                    phase = 8;
                    music.contentItem.grabToImage(result => {
                        result.saveToFile("/tmp/enclosure-music-mixes-wide.png");
                        music.minimumWidth=860; music.width = 900; music.height = 600; repeatStart = attempts; phase = 7;
                    });
                } else if (phase === 7 && attempts >= repeatStart + 3) {
                    const mixes = findItem(music.contentItem, "music-daily-mixes");
                    const previewCard = findItem(music.contentItem,"music-mix-preview-card");
                    const preview = findItem(music.contentItem,"music-mix-preview");
                    const pos = previewCard.mapToItem(mixes,0,0);
                    if (mixes.wide || pos.x < 0 || pos.y < 0 || pos.x+previewCard.width > mixes.width+1 || pos.y+previewCard.height > mixes.height+1 || preview.height < 100) { console.error("MIX_NARROW_LAYOUT_FAILED " + [pos.x,pos.y,previewCard.width,previewCard.height,mixes.width,mixes.height,preview.height]); Qt.exit(1); return; }
                    console.log("MIX_LAYOUT_PASSED");
                    console.log("MIX_PREVIEW_AND_DOWNLOAD_PASSED");
                    console.log("MUSIC_ACCEPTANCE_PASSED tracks=" + music.tracks.length + " queue=" + music.queue.length);
                    console.log('MUSIC_GEOMETRY ' + music.contentItem.width + 'x' + music.contentItem.height + ' children=' + music.contentItem.children.length + ' root=' + music.contentItem.children[music.contentItem.children.length-1].width); music.contentItem.grabToImage(result => { result.saveToFile("/tmp/enclosure-music-acceptance.png"); music.toggleFullscreen(); repeatStart = attempts; phase = 90; });
                } else if (phase === 90 && attempts >= repeatStart + 3) {
                    const stage = findItem(music.contentItem, "music-fullscreen-stage");
                    const art = findItem(music.contentItem, "music-fullscreen-art");
                    const transport = findItem(music.contentItem, "music-fullscreen-play");
                    const rail = findItem(music.contentItem, "music-fullscreen-seek");
                    if (!music.immersive || !stage.visible || !art.visible || art.width < 100 || !transport.enabled || !rail.enabled) { console.error("MUSIC_FULLSCREEN_ENTER_FAILED"); Qt.exit(1); return; }
                    const lyrics = findItem(music.contentItem, "music-fullscreen-lyrics");
                    const spectrum = findItem(music.contentItem, "music-fullscreen-spectrum");
                    const savedLyrics = music.lyricText;
                    music.lyricText = "";
                    if (lyrics.visible || !spectrum.visible || spectrum.width < 100 || spectrum.height < 100) { console.error("MUSIC_FULLSCREEN_SPECTRUM_MISSING"); Qt.exit(1); return; }
                    music.lyricText = "[00:00.00]Fullscreen test lyric";
                    if (!lyrics.visible || spectrum.visible || spectrum.captureAudio) { console.error("MUSIC_FULLSCREEN_LYRICS_RESTORE_FAILED"); Qt.exit(1); return; }
                    music.lyricText = savedLyrics;
                    console.log("MUSIC_FULLSCREEN_LYRICS_FALLBACK_PASSED");
                    const pos = transport.mapToItem(stage, 0, 0);
                    if (pos.y < 0 || pos.y + transport.height > stage.height) { console.error("MUSIC_FULLSCREEN_BOUNDS_FAILED"); Qt.exit(1); return; }
                    const add = findItem(music.contentItem, "music-fullscreen-add-current-to-playlist");
                    stop();
                    if (!transport.activeFocus || !tabTo(add)) { console.error("FULLSCREEN_INITIAL_FOCUS_FAILED", music.activeFocusItem); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Return);
                    phase = 901;
                    start();
                } else if (phase === 901) {
                    const choices = findItem(music.contentItem, "music-playlist-choices");
                    if (!choices?.itemAtIndex(2)) return;
                    if (!choices.activeFocus) { console.error("PLAYLIST_KEYBOARD_FOCUS_FAILED", music.activeFocusItem); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_End);
                    input.keyClick(Qt.Key_Return);
                    phase = 902;
                } else if (phase === 902 && !music.busy) {
                    if (music.playlists[2].paths[0] !== music.current.path) { console.error("MUSIC_FULLSCREEN_PLAYLIST_ADD_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Escape);
                    if (!music.immersive || findItem(music.contentItem, "music-playlist-choices")?.visible) { console.error("MUSIC_FULLSCREEN_PLAYLIST_PICKER_ESCAPE_FAILED"); Qt.exit(1); return; }
                    const selected = music.current.path;
                    findItem(music.contentItem, "music-fullscreen-exit").clicked();
                    if (music.immersive || music.current.path !== selected) { console.error("MUSIC_FULLSCREEN_RESTORE_FAILED"); Qt.exit(1); return; }
                    repeatStart = attempts; phase = 92;
                } else if (phase === 92 && attempts >= repeatStart + 3) {
                    music.toggleFullscreen(); music.requestActivate(); repeatStart = attempts; phase = 91;
                } else if (phase === 91 && attempts >= repeatStart + 3) {
                    music.contentItem.grabToImage(result => {
                        result.saveToFile("/tmp/enclosure-music-fullscreen.png");
                        input.keyClick(Qt.Key_Escape); repeatStart = attempts; phase = 93;

                    });
                    phase = 11;
                } else if (phase === 93 && attempts >= repeatStart + 3) {
                    if (music.immersive || !music.visible) { console.error("MUSIC_FULLSCREEN_ESCAPE_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_F11); repeatStart = attempts; phase = 94;
                } else if (phase === 94 && attempts >= repeatStart + 3) {
                    if (!music.immersive) { console.error("MUSIC_FULLSCREEN_F11_FAILED"); Qt.exit(1); return; }
                    stop();
                    console.log("MUSIC_FULLSCREEN_PASSED");
                    const library = findItem(music.contentItem, "music-background");
                    const close = findItem(music.contentItem, "music-fullscreen-library-close");
                    const previousPage = music.page, previousDetail = music.detail, previousQuery = music.query;
                    input.keyClick(Qt.Key_B, Qt.ControlModifier);
                    input.tryCompare(library, "reveal", 1, 2000);
                    if (!music.immersive || !close.activeFocus) { console.error("FULLSCREEN_LIBRARY_SHORTCUT_FAILED"); Qt.exit(1); return; }
                    for (const page of ["Songs", "Albums", "Artists", "Favorites", "Playlists", "Spotify playlists", "Downloads", "Now playing"]) {
                        input.mouseClick(findItem(music.contentItem, "music-navigation-" + page));
                        if (music.page !== page || !music.immersive) { console.error("FULLSCREEN_LIBRARY_NAVIGATION_FAILED", page); Qt.exit(1); return; }
                    }
                    input.keyClick(Qt.Key_Escape);
                    input.tryCompare(library, "visible", false, 2000);
                    if (!music.immersive) { console.error("FULLSCREEN_LIBRARY_ESCAPE_EXITED_FULLSCREEN"); Qt.exit(1); return; }
                    input.mouseMove(music.contentItem, music.width / 2, music.height / 2);
                    input.mouseMove(music.contentItem, music.width / 2, music.height - 2);
                    input.tryCompare(library, "reveal", 1, 2000);
                    input.keyClick(Qt.Key_B, Qt.ControlModifier);
                    input.tryCompare(library, "visible", false, 2000);
                    music.navigate(previousPage, previousDetail);
                    music.query = previousQuery;
                    console.log("MUSIC_FULLSCREEN_LIBRARY_PASSED");
                    music.spotifyPlayer = spotify;
                    if (!music.spotifyPreview) { console.error("SPOTIFY_AUTOFOLLOW_FAILED"); Qt.exit(1); return; }
                    music.control({action:"Pause"});
                    if (spotify.isPlaying) { console.error("SPOTIFY_REMOTE_PAUSE_FAILED"); Qt.exit(1); return; }
                    music.control({action:"Play"});
                    music.control({action:"Seek",offset:5000000});
                    if (!spotify.isPlaying || spotify.position !== 35) { console.error("SPOTIFY_REMOTE_PLAY_SEEK_FAILED"); Qt.exit(1); return; }
                    music.control({action:"Stop"});
                    if (spotify.isPlaying) { console.error("SPOTIFY_REMOTE_STOP_FAILED"); Qt.exit(1); return; }
                    spotify.play();
                    if (music.current.title !== "Suggested song" || music.playbackDuration !== 180000 || !music.playing) { console.error("SPOTIFY_METADATA_FAILED"); Qt.exit(1); return; }
                    music.lyricText = "";
                    phase = 941;
                    repeatStart = attempts;
                    start();
                } else if (phase === 941 && attempts >= repeatStart + 4) {
                    stop();
                    const spectrum = findItem(music.contentItem, "music-fullscreen-spectrum");
                    const peak = Math.max(...spectrum.levels);
                    const band = findItem(spectrum, "music-spectrum-band-" + spectrum.levels.indexOf(peak));
                    if (!spectrum.visible || !spectrum.captureAudio || peak < 0.25 || !band || band.height < 20) {
                        console.error("MUSIC_FULLSCREEN_SPECTRUM_RESPONSE_FAILED", spectrum.visible, spectrum.captureAudio, peak, band?.height);
                        Qt.exit(1); return;
                    }
                    const play = findItem(music.contentItem, "music-fullscreen-play");
                    input.keyClick(Qt.Key_Space);
                    if (spotify.isPlaying || music.playing || play.text !== "Play") { console.error("SPOTIFY_PAUSE_FAILED"); Qt.exit(1); return; }
                    if (spectrum.captureAudio || spectrum.levels.length !== 0) { console.error("MUSIC_FULLSCREEN_SPECTRUM_PAUSE_FAILED"); Qt.exit(1); return; }
                    console.log("MUSIC_FULLSCREEN_SPECTRUM_PASSED");
                    input.keyClick(Qt.Key_K);
                    input.keyClick(Qt.Key_H);
                    input.keyClick(Qt.Key_L);
                    if (spotify.previousCalls !== 1 || spotify.nextCalls !== 1) {
                        console.error("FULLSCREEN_TRACK_SHORTCUT_FAILED", spotify.previousCalls, spotify.nextCalls);
                        Qt.exit(1); return;
                    }
                    spotify.previousCalls = 0;
                    spotify.nextCalls = 0;
                    const rail = findItem(music.contentItem, "music-fullscreen-seek");
                    if (!tabTo(rail)) { console.error("FULLSCREEN_SEEK_FOCUS_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Right);
                    input.keyClick(Qt.Key_Right);
                    for (const name of ["next", "previous", "shuffle", "repeat"]) {
                        if (!tabTo(findItem(music.contentItem, "music-fullscreen-" + name))) { console.error("FULLSCREEN_TRANSPORT_FOCUS_FAILED", name); Qt.exit(1); return; }
                        input.keyClick(Qt.Key_Return);
                    }
                    const volume = findItem(music.contentItem, "music-fullscreen-volume");
                    const initialVolume = spotify.volume;
                    if (!tabTo(volume)) { console.error("FULLSCREEN_VOLUME_FOCUS_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Left);
                    if (!spotify.isPlaying || spotify.position !== 45 || spotify.nextCalls !== 1 || spotify.previousCalls !== 1 || !spotify.shuffle || spotify.loopState === 0 || Math.abs(spotify.volume - (initialVolume - 0.05)) > 0.001) {
                        console.error("SPOTIFY_TRANSPORT_FAILED", spotify.isPlaying, spotify.position, spotify.nextCalls, spotify.previousCalls, spotify.shuffle, spotify.loopState, spotify.volume);
                        Qt.exit(1); return;
                    }
                    spotify.canSeek = false; music.seek(60000);
                    if (spotify.position !== 45 || findItem(music.contentItem, "music-fullscreen-seek").enabled) { console.error("SPOTIFY_CAPABILITY_FAILED"); Qt.exit(1); return; }
                    const originalTracks = music.tracks;
                    const originalQueue = music.queue;
                    const originalPlaylists = music.playlists;
                    const uri = spotify.metadata["xesam:url"];
                    const suggestion = {uri: uri, title: "Suggested song", artist: "Suggested artist"};
                    music.tracks = originalTracks.map((track, i) => i === 0 ? Object.assign({}, track, {spotifyUri: uri}) : track);
                    music.playlists = originalPlaylists.concat([{id: "queue-test", paths: []}]);
                    music.navigate("Playlist", "queue-test");
                    music.spotifySuggestions = {playlist: "queue-test", pending: false, tracks: [suggestion]};
                    input.keyClick(Qt.Key_Q);
                    if (!tabTo(findItem(music.contentItem, "music-fullscreen-suggestions-tab"))) { console.error("SUGGESTIONS_TAB_FOCUS_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Return);
                    const queueCurrent = findItem(music.contentItem, "music-fullscreen-queue-current");
                    const suggestions = findItem(music.contentItem, "music-fullscreen-suggestions");
                    if (!queueCurrent.visible || !queueCurrent.enabled || !suggestions.visible || suggestions.count !== 1) { console.error("FULLSCREEN_QUEUE_MENU_FAILED"); Qt.exit(1); return; }
                    if (!tabTo(suggestions)) { console.error("SUGGESTIONS_LIST_FOCUS_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Down);
                    input.keyClick(Qt.Key_Return);
                    if (spotify.isPlaying) { console.error("SUGGESTION_KEYBOARD_PLAY_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Return);
                    input.keyClick(Qt.Key_Right);
                    if (music.queue.length !== originalQueue.length + 1 || music.queue[music.queue.length - 1].spotifyUri !== uri || !spotify.isPlaying || music.playlists[music.playlists.length - 1].paths.length !== 0) { console.error("FULLSCREEN_QUEUE_SUGGESTION_FAILED"); Qt.exit(1); return; }
                    if (!tabTo(findItem(music.contentItem, "music-fullscreen-queue-tab"))) { console.error("QUEUE_TAB_FOCUS_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Return);
                    const queue = findItem(music.contentItem, "music-fullscreen-queue-list");
                    if (!tabTo(queue)) { console.error("QUEUE_LIST_FOCUS_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Down);
                    input.keyClick(Qt.Key_Return);
                    if (music.spotifyPreview || music.currentIndex !== originalQueue.length || spotify.isPlaying) { console.error("QUEUE_KEYBOARD_SELECT_FAILED"); Qt.exit(1); return; }
                    const addSongs = findItem(music.contentItem, "music-fullscreen-add-songs");
                    const queueSearch = findItem(music.contentItem, "music-fullscreen-queue-search");
                    const library = findItem(music.contentItem, "music-fullscreen-queue-library");
                    if (!tabTo(addSongs)) { console.error("QUEUE_ADD_SONGS_FOCUS_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Return);
                    if (!queueSearch.inputActiveFocus || library.count !== originalTracks.length) { console.error("QUEUE_LIBRARY_OPEN_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Q);
                    input.keyClick(Qt.Key_K);
                    input.keyClick(Qt.Key_Space);
                    input.keyClick(Qt.Key_H);
                    input.keyClick(Qt.Key_L);
                    if (queueSearch.text.toLowerCase() !== "qk hl" || library.count !== 0) { console.error("QUEUE_SEARCH_SHORTCUT_CONFLICT", queueSearch.text, library.count); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_A, Qt.ControlModifier);
                    input.keyClick(Qt.Key_2);
                    if (queueSearch.text !== "2" || library.count !== 1) { console.error("QUEUE_LIBRARY_FILTER_FAILED", queueSearch.text, library.count); Qt.exit(1); return; }
                    const queuedCount = music.queue.length;
                    const playingIndex = music.currentIndex;
                    input.keyClick(Qt.Key_Down);
                    input.keyClick(Qt.Key_Return);
                    if (music.queue.length !== queuedCount + 1 || music.queue[queuedCount].path !== originalTracks[1].path ||
                        music.currentIndex !== playingIndex) { console.error("QUEUE_LIBRARY_KEYBOARD_FAILED"); Qt.exit(1); return; }
                    const result = library.itemAtIndex(0);
                    if (!result) { console.error("QUEUE_LIBRARY_RESULT_MISSING"); Qt.exit(1); return; }
                    input.mouseClick(result, result.width / 2, result.height / 2);
                    if (music.queue.length !== queuedCount + 2 || music.queue[queuedCount + 1].path !== originalTracks[1].path ||
                        music.currentIndex !== playingIndex || !findItem(music.contentItem, "music-fullscreen-queue-added").visible) {
                        console.error("QUEUE_LIBRARY_CLICK_FAILED"); Qt.exit(1); return;
                    }
                    console.log("MUSIC_FULLSCREEN_QUEUE_LIBRARY_PASSED");
                    if (!tabTo(findItem(music.contentItem, "music-fullscreen-suggestions-tab"))) { console.error("SUGGESTIONS_TAB_RESTORE_FAILED"); Qt.exit(1); return; }
                    input.keyClick(Qt.Key_Return);
                    input.keyClick(Qt.Key_Q);
                    music.tracks = originalTracks;
                    music.queue = originalQueue;
                    music.playlists = originalPlaylists;
                    console.log("MUSIC_FULLSCREEN_QUEUE_PASSED");
                    console.log("MUSIC_FULLSCREEN_KEYBOARD_PASSED");
                    music.select(0);
                    if (music.spotifyPreview || spotify.isPlaying || music.current.title === "Suggested song") { console.error("SPOTIFY_LOCAL_RETURN_FAILED"); Qt.exit(1); return; }
                    console.log("MUSIC_SPOTIFY_FULLSCREEN_PASSED");
                    music.toggleFullscreen();
                    // Resize the content area directly because the tiled window is sized by Niri.
                    findItem(music.contentItem, "music-background").anchors.bottomMargin = -200;
                    music.page = "Playlist"; music.detail = "test";
                    music.spotifySuggestions = {playlist:"test",pending:false,hasMore:true,tracks:Array.from({length:14}, (_,i)=>({uri:"spotify:track:"+String(i).padStart(22,"0"),title:"Suggestion "+i,artist:"New artist"}))};
                    repeatStart = attempts; phase = 95;
                    start();
                } else if (phase === 950) {
                    const suggestions = findItem(music.contentItem, "music-playlist-suggestions");
                    const songs = findItem(music.contentItem, "music-track-row-0")?.ListView.view;
                    if (suggestions.height >= 4 * music.suggestionRowHeight || !songs || songs.height < songs.contentHeight) {
                        console.error("MUSIC_SHORT_PLAYLIST_LAYOUT_FAILED", suggestions.height, songs?.height, songs?.contentHeight);
                        Qt.exit(1); return;
                    }
                    findItem(music.contentItem, "music-background").anchors.bottomMargin = -200;
                    repeatStart = attempts; phase = 95;
                } else if (phase === 95 && attempts >= repeatStart + 3) {
                    const list = findItem(music.contentItem, "music-playlist-suggestions");
                    if (list.count !== 14 || !findItem(music.contentItem, "music-suggestions-load-more")?.enabled) { console.error("SUGGESTIONS_CONTINUOUS_LIST_FAILED"); Qt.exit(1); return; }
                    if (Math.abs(list.height - 4 * music.suggestionRowHeight) > 1) { console.error("SUGGESTIONS_VIEWPORT_HEIGHT_FAILED", list.height); Qt.exit(1); return; }
                    if (!checkedShortPlaylist) {
                        checkedShortPlaylist = true;
                        findItem(music.contentItem, "music-background").anchors.bottomMargin = 0;
                        phase = 950;
                        return;
                    }
                    const firstSuggestion = list.itemAtIndex(0);
                    if (!firstSuggestion || firstSuggestion.selected || firstSuggestion.height >= findItem(music.contentItem, "music-track-row-0").height) { console.error("SUGGESTION_COMPACT_ROW_FAILED"); Qt.exit(1); return; }
                    music.play(music.tracks, 0);
                    music.next(false);
                    if (music.currentIndex !== 1 || music.requestedPreview) { console.error("PLAYLIST_NEXT_SKIPPED_LOCAL_QUEUE"); Qt.exit(1); return; }
                    firstSuggestion.playRequested();
                    if (music.requestedPreview !== firstSuggestion.track.uri) { console.error("SUGGESTION_ROW_PLAY_FAILED"); Qt.exit(1); return; }
                    music.requestedPreview = "";
                    spotify.play();
                    music.next(false);
                    if (music.requestedPreview || spotify.nextCalls !== 2) { console.error("NEXT_RESTARTED_SUGGESTIONS"); Qt.exit(1); return; }
                    spotify.metadata = {"xesam:url": "https://open.spotify.com/track/" + firstSuggestion.track.uri.split(":").pop() + "?si=test"};
                    if (!firstSuggestion.selected) { console.error("SUGGESTION_SELECTION_FAILED"); Qt.exit(1); return; }
                    firstSuggestion.playRequested();
                    if (spotify.isPlaying) { console.error("SUGGESTION_ROW_PAUSE_FAILED"); Qt.exit(1); return; }
                    firstSuggestion.playRequested();
                    if (!spotify.isPlaying) { console.error("SUGGESTION_ROW_RESUME_FAILED"); Qt.exit(1); return; }
                    spotify.canGoNext = false;
                    music.toggleFullscreen();
                    findItem(music.contentItem, "music-fullscreen-queue-toggle").clicked();
                    repeatStart = attempts; phase = 951;
                } else if (phase === 951 && attempts >= repeatStart + 3) {
                    const stage = findItem(music.contentItem, "music-fullscreen-stage");
                    const panel = findItem(music.contentItem, "music-fullscreen-queue-panel");
                    const art = findItem(music.contentItem, "music-fullscreen-art");
                    const rail = findItem(music.contentItem, "music-fullscreen-seek");
                    const next = findItem(music.contentItem, "music-fullscreen-next");
                    const panelPos = panel.mapToItem(stage, 0, 0);
                    const artPos = art.mapToItem(stage, 0, 0);
                    const railPos = rail.mapToItem(stage, 0, 0);
                    if (!music.immersive || !panel.visible || !next.visible || !next.enabled ||
                        panelPos.x + panel.width > stage.width || artPos.x + art.width > panelPos.x ||
                        panelPos.y + panel.height > railPos.y) { console.error("FULLSCREEN_QUEUE_BOUNDS_FAILED"); Qt.exit(1); return; }
                    const nextTitle = findItem(music.contentItem, "music-fullscreen-up-next-title");
                    if (!nextTitle.visible || nextTitle.text !== music.suggestedTracks[1].title) { console.error("FULLSCREEN_SUGGESTED_NEXT_TITLE_FAILED"); Qt.exit(1); return; }
                    next.clicked();
                    if (music.requestedPreview !== music.suggestedTracks[1].uri) { console.error("FULLSCREEN_NEXT_BUTTON_FAILED"); Qt.exit(1); return; }
                    music.requestedPreview = "";
                    music.contentItem.grabToImage(result => result.saveToFile("/tmp/enclosure-music-fullscreen-queue.png"));
                    const target = MprisController.nextPlayer(spotify);
                    if (target?.dbusName !== "org.mpris.MediaPlayer2.enclosure_music" || !music.canNext) { console.error("SUGGESTION_MEDIA_NEXT_ROUTE_FAILED"); Qt.exit(1); return; }
                    target.next();
                    repeatStart = attempts; phase = 952;
                } else if (phase === 952 && attempts >= repeatStart + 3) {
                    if (music.requestedPreview !== music.suggestedTracks[1].uri || spotify.nextCalls !== 2) { console.error("SUGGESTION_MEDIA_NEXT_FAILED", music.requestedPreview, music.suggestedTracks[1].uri, spotify.nextCalls, music.notice); Qt.exit(1); return; }
                    const suggestions = findItem(music.contentItem, "music-fullscreen-suggestions");
                    spotify.metadata = {"xesam:url": music.requestedPreview};
                    if (!music.immersive || !suggestions.visible || suggestions.currentIndex !== 1 ||
                        !suggestions.itemAtIndex(1)?.selected) { console.error("FULLSCREEN_SUGGESTION_SELECTION_FAILED"); Qt.exit(1); return; }
                    music.requestedPreview = "";
                    GlobalStates.musicWindowVisible = false;
                    spotify.pause();
                    spotify.position = spotify.length - 0.1;
                    repeatStart = attempts; phase = 953;
                } else if (phase === 953 && attempts >= repeatStart + 3) {
                    if (music.requestedPreview) { console.error("PAUSED_SUGGESTION_ADVANCED"); Qt.exit(1); return; }
                    spotify.loopState = MprisLoopState.Track;
                    spotify.play();
                    repeatStart = attempts; phase = 954;
                } else if (phase === 954 && attempts >= repeatStart + 3) {
                    if (music.requestedPreview) { console.error("LOOPING_SUGGESTION_ADVANCED"); Qt.exit(1); return; }
                    spotify.loopState = MprisLoopState.None;
                    repeatStart = attempts; phase = 955;
                } else if (phase === 955 && attempts >= repeatStart + 3) {
                    if (music.requestedPreview !== music.suggestedTracks[2].uri) { console.error("HIDDEN_SUGGESTION_AUTOPLAY_FAILED"); Qt.exit(1); return; }
                    music.requestedPreview = "";
                    repeatStart = attempts; phase = 956;
                } else if (phase === 956 && attempts >= repeatStart + 3) {
                    if (music.requestedPreview) { console.error("SUGGESTION_AUTOPLAY_REPEATED"); Qt.exit(1); return; }
                    spotify.position = 30;
                    GlobalStates.musicWindowVisible = true;
                    console.log("MUSIC_SUGGESTION_AUTOPLAY_PASSED");
                    spotify.canGoNext = true;
                    const suggestions = music.suggestedTracks;
                    spotify.metadata = {"xesam:url": suggestions[suggestions.length - 1].uri};
                    music.navigate("Albums");
                    music.next(false);
                    if (!music.canNext || music.requestedPreview !== suggestions[0].uri || spotify.nextCalls !== 2) { console.error("SUGGESTION_QUEUE_WRAP_AFTER_NAVIGATION_FAILED"); Qt.exit(1); return; }
                    music.page = "Playlist"; music.detail = "test";
                    music.spotifySuggestions = {playlist:"test",pending:false,hasMore:true,tracks:suggestions};
                    console.log("MUSIC_FULLSCREEN_SUGGESTION_MEDIA_NEXT_PASSED");
                    findItem(music.contentItem, "music-fullscreen-queue-tab").clicked();
                    music.select(0);
                    const queue = findItem(music.contentItem, "music-fullscreen-queue-list");
                    if (!queue.visible || queue.count !== music.queue.length || queue.currentIndex !== 0) { console.error("FULLSCREEN_QUEUE_TAB_FAILED"); Qt.exit(1); return; }
                    const nextTitle = findItem(music.contentItem, "music-fullscreen-up-next-title");
                    if (!nextTitle.visible || nextTitle.text !== music.queue[1].title) { console.error("FULLSCREEN_LOCAL_NEXT_TITLE_FAILED"); Qt.exit(1); return; }
                    console.log("MUSIC_FULLSCREEN_UP_NEXT_PASSED");
                    music.play(music.tracks, 1);
                    phase = 957;
                } else if (phase === 957 && music.playing && music.playbackDuration > 3500) {
                    music.toggle();
                    music.seek(3400);
                    phase = 958;
                } else if (phase === 958 && music.playbackPosition > 3000) {
                    const previous = findItem(music.contentItem, "music-fullscreen-previous");
                    if (!music.immersive || !previous.enabled) { console.error("FULLSCREEN_PREVIOUS_UNAVAILABLE"); Qt.exit(1); return; }
                    previous.click();
                    if (music.currentIndex !== 0) { console.error("FULLSCREEN_PREVIOUS_LOCAL_FAILED"); Qt.exit(1); return; }
                    console.log("MUSIC_FULLSCREEN_PREVIOUS_LOCAL_PASSED");
                    music.toggleFullscreen();
                    const list = findItem(music.contentItem, "music-playlist-suggestions");
                    list.positionViewAtIndex(8, ListView.Beginning);
                    repeatStart = attempts; phase = 96;
                } else if (phase === 96 && attempts >= repeatStart + 3) {
                    const list = findItem(music.contentItem, "music-playlist-suggestions");
                    const row = list.itemAtIndex(8);
                    if (list.contentY <= 0 || !row || row.modelData.title !== "Suggestion 8" || list.model[0].title !== "Suggestion 0") { console.error("SUGGESTIONS_SCROLL_LOAD_FAILED"); Qt.exit(1); return; }
                    const more = findItem(music.contentItem, "music-suggestions-load-more");
                    more.clicked();
                    if (more.enabled || !music.spotifySuggestions.pending || list.count !== 14) { console.error("SUGGESTIONS_LOAD_MORE_FAILED"); Qt.exit(1); return; }
                    const tracks = Array.from({length:150}, (_,i)=>({uri:"spotify:track:"+String(i).padStart(22,"0"),title:"Suggestion "+i,artist:"New artist"}));
                    music.receive(JSON.stringify({id:music.requestId,ok:true,data:{playlist:"test",pending:false,hasMore:false,tracks:tracks}}));
                    if (more.visible) { console.error("SUGGESTIONS_EXHAUSTED_FAILED"); Qt.exit(1); return; }
                    repeatStart = attempts; phase = 97;
                } else if (phase === 97 && attempts >= repeatStart + 3) {
                    const list = findItem(music.contentItem, "music-playlist-suggestions");
                    if (list.count !== 150 || list.contentY <= 0) { console.error("SUGGESTIONS_APPEND_SCROLL_FAILED"); Qt.exit(1); return; }
                    music.spotifySuggestions = {playlist:"test",pending:false,tracks:[]};
                    if (list.count !== 0) { console.error("SUGGESTIONS_RESET_FAILED"); Qt.exit(1); return; }
                    console.log("MUSIC_SUGGESTIONS_CONTINUOUS_PASSED"); stop(); Qt.quit();
                }
            }
        }
    }
    '''
        (config/'shell.qml').write_text(qml)
        env={**os.environ,'PATH':f"{audio_bin}:{os.environ['PATH']}",'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),
             'XDG_STATE_HOME':str(home/'.local/state'),'XDG_CACHE_HOME':str(home/'.cache'),
             'XDG_DATA_HOME':str(home/'.local/share'),'QT_QPA_PLATFORM':os.environ.get('MUSIC_TEST_PLATFORM','offscreen'),
             'QT_AUDIO_BACKEND':os.environ.get('QT_AUDIO_BACKEND','pulseaudio'),
             'QS_DISABLE_FILE_WATCHER':'1','PYTHONDONTWRITEBYTECODE':'1'}
        result=subprocess.run(['quickshell','-p',str(config)],env=env,capture_output=True,text=True,timeout=25)
        print(result.stdout)
        print(result.stderr)
        if result.returncode or 'MUSIC_SUGGESTIONS_CONTINUOUS_PASSED' not in result.stdout+result.stderr:
            raise SystemExit(1)
        import json
        state=json.loads((home/'.local/state/enclosure/music/library.json').read_text())
        assert len(state['favorites'])==1 and len(state['playlists'][0]['paths'])==2, state
        assert next(p for p in state['playlists'] if p['id'] == 'regular-add')['paths'] == [], state
        assert len(next(p for p in state['playlists'] if p['id'] == 'fullscreen-add')['paths']) == 1, state
        print('Music playback, queue, seek, lyrics and persisted favorites/playlists verified.')


def main():
    if '--session' in sys.argv:
        session()
        return
    missing = [name for name in ('Xvfb','niri','quickshell','ffmpeg','dbus-run-session') if not __import__('shutil').which(name)]
    if missing:
        raise SystemExit('Missing acceptance tools: ' + ', '.join(missing))
    spec = importlib.util.spec_from_file_location('music_wayland', ROOT/'desktop/scripts/check_wayland.py')
    wayland = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wayland)
    with tempfile.TemporaryDirectory(prefix='music-wayland-') as directory:
        root = Path(directory)
        (root/'runtime').mkdir(mode=0o700)
        env = wayland.isolated_environment(root)
        with (root/'xvfb.log').open('w') as log:
            xvfb = subprocess.Popen(['Xvfb','-displayfd','1','-screen','0','1600x1000x24','-nolisten','tcp'],env=env,stdout=subprocess.PIPE,stderr=log,text=True)
            compositor = None
            try:
                env['DISPLAY'] = ':' + xvfb.stdout.readline().strip()
                (root/'niri.kdl').write_text('hotkey-overlay { skip-at-startup; }\n')
                with (root/'niri.log').open('w') as compositor_log:
                    compositor = subprocess.Popen(['niri','-c',str(root/'niri.kdl')],env=env,stdout=compositor_log,stderr=compositor_log)
                    wayland.wait_for_niri(compositor,root,env)
                    env['MUSIC_TEST_PLATFORM'] = 'wayland'
                    env['GSETTINGS_BACKEND'] = 'memory'
                    result = subprocess.run(['dbus-run-session','--',sys.executable,__file__,'--session'],env=env,timeout=40)
                    if result.returncode:
                        raise SystemExit(result.returncode)
            finally:
                if compositor:
                    wayland.stop(compositor)
                wayland.stop(xvfb)


if __name__ == '__main__':
    main()
