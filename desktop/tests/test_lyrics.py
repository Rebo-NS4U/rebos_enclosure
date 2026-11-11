"""Exercise real QML service with isolated player and transport fixtures."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

APP = Path(__file__).resolve().parents[2] / 'system/apps/shell'
PLAYER = '''pragma Singleton
import QtQuick
import Quickshell
Singleton {
 property var activePlayer: ({dbusName: 'test', identity: 'Spotify', metadata: {'xesam:asText':'[00:01.00]First\\n[00:03.00]Second'}, trackAlbum:''})
 property string trackTitle: 'Test'
 property string trackArtists: 'Artist'
 property real position: 1.5
 property real length: 10
}
'''
HARNESS = '''import QtQuick
import Quickshell
import qs.modules.services
import qs.modules.components
import "modules/services/Lyrics.js" as Parser
ShellRoot {
 Item {
  LyricsSection { id: menuSection; width: 216 }
  LyricsSection { id: pinnedSection; width: 540; compact: true }
 }
 Timer { interval: 600; running: true; onTriggered: {
  try {
   function check(ok, message) { if (!ok) throw Error(message); }
   check(LyricsService.lines.length === 2 && LyricsService.currentLine === 0 && LyricsService.provider === 'Spotify', 'Player priority');
   MprisController.position = 3.5;
   check(Parser.activeLine(LyricsService.lines, 3.5) === 1, 'Seek forward');
   check(Parser.activeLine(LyricsService.lines, 0) === -1, 'Seek backward');
   const parsed = Parser.parseLrc('[offset:-500]\\n[00:01.50][00:03.00]Repeated\\n[ar:Artist]');
   check(parsed.length === 2 && parsed[0].time === 1 && parsed[1].time === 2.5, 'LRC offsets/multiple timestamps');
   LyricsService.pin('bottom', 'test');
   check(LyricsService.pinEdge === 'bottom' && LyricsService.pinScreen === 'test', 'Bottom pin');
   LyricsService.pin('top', 'test');
   check(LyricsService.pinEdge === 'top', 'Move pin');
   LyricsService.pinEdge = '';
   let requests = [];
   LyricsService.createRequest = () => {
    const xhr = {readyState: 0, status: 0, responseText: '', abort: () => {}, open: () => {}, setRequestHeader: () => {}, send: () => {}};
    requests.push(xhr); return xhr;
   };
   MprisController.activePlayer = {dbusName: 'test', identity: 'Spotify', metadata: {}, trackAlbum: ''};
   LyricsService.refresh();
   const old = requests[0];
   check(!!old, 'Online fallback');
   MprisController.trackTitle = 'Next song'; LyricsService.refresh();
   old.readyState = XMLHttpRequest.DONE; old.status = 200;
   old.responseText = JSON.stringify({plainLyrics: 'Stale'}); old.onreadystatechange();
   check(LyricsService.plain === '', 'Stale response discarded');
   const current = requests[1]; current.readyState = XMLHttpRequest.DONE; current.status = 200;
   current.responseText = JSON.stringify({plainLyrics: 'Plain lyrics'}); current.onreadystatechange();
   check(LyricsService.plain === 'Plain lyrics' && LyricsService.provider === 'LRCLIB', 'Plain fallback');
   LyricsService.refresh(); check(requests.length === 2, 'Cached result reused');
   MprisController.trackTitle = 'Missing'; LyricsService.refresh();
   const missing = requests[2]; missing.readyState = XMLHttpRequest.DONE; missing.status = 404; missing.onreadystatechange();
   check(LyricsService.status.includes('No lyrics') && !LyricsService.plain, 'Missing lyrics clears previous song');
   LyricsService.apply('', 'LRCLIB', true);
   check(LyricsService.status.includes('Instrumental'), 'Instrumental state');
   console.log('PASS: lyrics parsing, priority, fallback, cache, stale requests, seeking and pin controls'); idleCheck.start();
  } catch (error) { console.error(error); Qt.exit(1); }
 } }
 Timer { id: idleCheck; interval: 3300; repeat: true; property int phase: 0
 onTriggered: {
  try {
   if (phase === 0) {
    if (pinnedSection.controlsVisible || pinnedSection.backgroundOpacity !== 0 || !menuSection.controlsVisible)
     throw Error('Idle view must show lyrics only; menu must remain usable');
    pinnedSection.revealControls();
    if (!pinnedSection.controlsVisible) throw Error('Interaction did not reveal options');
    phase++; return;
   }
   if (phase === 1) {
    if (pinnedSection.controlsVisible) throw Error('Controls did not hide again');
    pinnedSection.autoHideControls = false;
    phase++; return;
   }
   if (!pinnedSection.controlsVisible || pinnedSection.backgroundOpacity === 0) throw Error('Auto-hide opt-out failed');
   console.log('PASS: real idle timer, interaction reveal, repeat hide and opt-out'); Qt.quit();
  } catch(error) { console.error(error); Qt.exit(1); }
 } }
}
'''

@unittest.skipUnless(shutil.which('quickshell'), 'Quickshell required')
class Lyrics(unittest.TestCase):
    def test_lyrics(self):
        with tempfile.TemporaryDirectory(prefix='lyrics-test-') as directory:
            root = Path(directory)
            for name in ('modules', 'config', 'assets'):
                shutil.copytree(APP / name, root / name)
            (root / 'modules/services/MprisController.qml').write_text(PLAYER)
            (root / 'shell.qml').write_text(HARNESS)
            (root / 'runtime').mkdir(mode=0o700)
            env = dict(os.environ, HOME=str(root), XDG_RUNTIME_DIR=str(root / 'runtime'),
                       QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_QPA_PLATFORMTHEME='basic')
            for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
                env.pop(key, None)
            for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
                env[key] = str(root / key.lower())
            result = subprocess.run(['quickshell', '-p', str(root), '--no-color'], env=env,
                                    capture_output=True, text=True, timeout=15)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('PASS:', output)
            self.assertNotIn('ERROR', output)

if __name__ == '__main__': unittest.main()
