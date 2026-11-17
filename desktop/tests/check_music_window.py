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
    import Quickshell
    import qs.modules.widgets.music
    import qs.modules.globals
    ShellRoot {
        MusicWindow { id: music }
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
                    if (music.page !== "Home" || music.queue.length !== 2) { console.error("MUSIC_CARD_PLAY_FAILED"); Qt.exit(1); }
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
                    music.navigate("Daily Mixes");

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
                    navButton.clicked();
                    if (music.page !== "Songs") { console.error("MUSIC_TOP_NAV_FAILED"); Qt.exit(1); return; }
                    music.navigate("Daily Mixes");
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
                    if (mixes.wide || pos.x < 0 || pos.y < 0 || pos.x+previewCard.width > mixes.width+1 || pos.y+previewCard.height > mixes.height+1 || preview.height < 100) { console.error("MIX_NARROW_LAYOUT_FAILED"); Qt.exit(1); return; }
                    console.log("MIX_LAYOUT_PASSED");
                    console.log("MIX_PREVIEW_AND_DOWNLOAD_PASSED");
                    console.log("MUSIC_ACCEPTANCE_PASSED tracks=" + music.tracks.length + " queue=" + music.queue.length);
                    console.log('MUSIC_GEOMETRY ' + music.contentItem.width + 'x' + music.contentItem.height + ' children=' + music.contentItem.children.length + ' root=' + music.contentItem.children[music.contentItem.children.length-1].width); music.contentItem.grabToImage(result => { result.saveToFile("/tmp/enclosure-music-acceptance.png"); Qt.quit(); });
                    stop();
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
