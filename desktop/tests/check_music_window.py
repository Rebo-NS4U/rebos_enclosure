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
        qml = '''//@ pragma UseQApplication
    import QtQuick
    import Quickshell
    import qs.modules.widgets.music
    import qs.modules.globals
    ShellRoot {
        MusicWindow { id: music }
        Component.onCompleted: GlobalStates.musicWindowVisible = true
        Timer {
            property int attempts: 0
            property int phase: 0
            interval: 200; running: true; repeat: true
            onTriggered: {
                attempts++;
                if (attempts > 90) { console.error("MUSIC_ACCEPTANCE_TIMEOUT " + music.notice); Qt.exit(1); }
                if (phase === 0 && !music.busy && music.tracks.length === 2) {
                    music.volume = 0;
                    music.play(music.tracks,0);
                    phase = 1;
                } else if (phase === 1 && music.playing) {
                    if (music.lyricLines.length !== 2) { console.error("MUSIC_LYRICS_FAILED"); Qt.exit(1); }
                    music.seek(1200);
                    music.favorite(music.current);
                    music.playlists = [{id:"test",name:"Acceptance",paths:music.queue.map(t=>t.path)}];
                    music.save();
                    music.next(false);
                    phase = 2;
                } else if (phase === 2 && music.currentIndex === 1 && music.playing) {
                    music.control({action:"Pause"});
                    music.navigate("Albums");
                    phase = 3;
                } else if (phase === 3 && !music.playing) {
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
