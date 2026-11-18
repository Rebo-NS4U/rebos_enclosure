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
    import qs.modules.widgets.music
    import qs.modules.globals
    ShellRoot {
        TestCase { id: input; when: false }
        MusicWindow { id: music }
        QtObject {
            id: spotify
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
        Component.onCompleted: GlobalStates.musicWindowVisible = true
        Timer {
            property int attempts: 0
            property int phase: 0
            property int repeatStart: 0
            interval: 200; running: true; repeat: true
            onTriggered: {
                attempts++;
                if (attempts > 90) { console.error("MUSIC_ACCEPTANCE_TIMEOUT " + music.notice); Qt.exit(1); }
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
                    if (music.queue.length !== 100 || music.currentIndex !== 0) { console.error("MUSIC_QUEUE_CAP_FAILED"); Qt.exit(1); }
                    const firstQueued = music.queue[0];
                    music.enqueue(music.tracks[0]);
                    if (music.queue.length !== 100 || music.queue[0] !== firstQueued || !music.notice.includes("full")) { console.error("MUSIC_QUEUE_FULL_FAILED"); Qt.exit(1); }
                    music.play(largeQueue, 149);
                    if (music.queue.length !== 100 || music.current.title !== "Queue song 149") { console.error("MUSIC_QUEUE_SELECTED_FAILED"); Qt.exit(1); }
                    music.play(music.tracks.slice(0, 1), 0);
                    music.enqueue(music.tracks[1]);
                    if (music.queue.length !== 2 || music.queue[1].path !== music.tracks[1].path) { console.error("MUSIC_QUEUE_APPEND_FAILED"); Qt.exit(1); }
                    const playCard = findItem(music.contentItem, "music-card-play");
                    if (!playCard) return;
                    playCard.clicked();
                    if (music.currentIndex < 0 || music.currentIndex >= music.queue.length) { console.error("MUSIC_RANDOM_START_FAILED"); Qt.exit(1); }
                    music.play(music.queue, 0);
                    if (music.currentIndex !== 0) { console.error("MUSIC_EXPLICIT_START_FAILED"); Qt.exit(1); }
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
                    music.playlists = [{id:"test",name:"Acceptance",paths:music.queue.map(t=>t.path).reverse()}];
                    music.save();
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
                    const pos = transport.mapToItem(stage, 0, 0);
                    if (pos.y < 0 || pos.y + transport.height > stage.height) { console.error("MUSIC_FULLSCREEN_BOUNDS_FAILED"); Qt.exit(1); return; }
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
                    console.log("MUSIC_FULLSCREEN_PASSED");
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
                    const play = findItem(music.contentItem, "music-fullscreen-play");
                    play.clicked();
                    if (spotify.isPlaying || music.playing || play.text !== "Play") { console.error("SPOTIFY_PAUSE_FAILED"); Qt.exit(1); return; }
                    play.clicked();
                    music.seek(45000);
                    findItem(music.contentItem, "music-fullscreen-next").clicked();
                    findItem(music.contentItem, "music-fullscreen-previous").clicked();
                    findItem(music.contentItem, "music-fullscreen-shuffle").clicked();
                    findItem(music.contentItem, "music-fullscreen-repeat").clicked();
                    const volume = findItem(music.contentItem, "music-fullscreen-volume");
                    volume.value = 0.3; volume.moved();
                    if (!spotify.isPlaying || spotify.position !== 45 || spotify.nextCalls !== 1 || spotify.previousCalls !== 1 || !spotify.shuffle || spotify.loopState === 0 || Math.abs(spotify.volume-0.3) > 0.01) { console.error("SPOTIFY_TRANSPORT_FAILED"); Qt.exit(1); return; }
                    spotify.canSeek = false; music.seek(60000);
                    if (spotify.position !== 45 || findItem(music.contentItem, "music-fullscreen-seek").enabled) { console.error("SPOTIFY_CAPABILITY_FAILED"); Qt.exit(1); return; }
                    music.select(0);
                    if (music.spotifyPreview || spotify.isPlaying || music.current.title === "Suggested song") { console.error("SPOTIFY_LOCAL_RETURN_FAILED"); Qt.exit(1); return; }
                    console.log("MUSIC_SPOTIFY_FULLSCREEN_PASSED");
                    music.toggleFullscreen();
                    music.page = "Playlist"; music.detail = "test";
                    music.spotifySuggestions = {playlist:"test",pending:false,tracks:Array.from({length:14}, (_,i)=>({uri:"spotify:track:"+String(i).padStart(22,"0"),title:"Suggestion "+i,artist:"New artist"}))};
                    repeatStart = attempts; phase = 95;
                } else if (phase === 95 && attempts >= repeatStart + 3) {
                    const list = findItem(music.contentItem, "music-playlist-suggestions");
                    if (list.count !== 14 || findItem(music.contentItem, "music-suggestions-next")) { console.error("SUGGESTIONS_CONTINUOUS_LIST_FAILED"); Qt.exit(1); return; }
                    list.positionViewAtIndex(8, ListView.Beginning);
                    repeatStart = attempts; phase = 96;
                } else if (phase === 96 && attempts >= repeatStart + 3) {
                    const list = findItem(music.contentItem, "music-playlist-suggestions");
                    const row = list.itemAtIndex(8);
                    if (list.contentY <= 0 || !row || row.modelData.title !== "Suggestion 8" || list.model[0].title !== "Suggestion 0") { console.error("SUGGESTIONS_SCROLL_LOAD_FAILED"); Qt.exit(1); return; }
                    music.applySuggestions({playlist:"test",pending:false,hasMore:false,tracks:Array.from({length:150}, (_,i)=>({uri:"spotify:track:"+String(i).padStart(22,"0"),title:"Suggestion "+i,artist:"New artist"}))}, false);
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
        env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),
             'XDG_STATE_HOME':str(home/'.local/state'),'XDG_CACHE_HOME':str(home/'.cache'),
             'XDG_DATA_HOME':str(home/'.local/share'),'QT_QPA_PLATFORM':os.environ.get('MUSIC_TEST_PLATFORM','offscreen'),
             'QT_AUDIO_BACKEND':os.environ.get('QT_AUDIO_BACKEND','pulseaudio'),
             'QS_DISABLE_FILE_WATCHER':'1','PYTHONDONTWRITEBYTECODE':'1'}
        result=subprocess.run(['quickshell','-p',str(config)],env=env,capture_output=True,text=True,timeout=25)
        print(result.stdout)
        print(result.stderr)
        if result.returncode or 'MUSIC_ACCEPTANCE_PASSED' not in result.stdout+result.stderr:
            raise SystemExit(1)
        import json
        state=json.loads((home/'.local/state/enclosure/music/library.json').read_text())
        assert len(state['favorites'])==1 and len(state['playlists'][0]['paths'])==2, state
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
