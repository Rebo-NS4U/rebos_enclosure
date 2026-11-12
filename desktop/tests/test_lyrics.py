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
 property bool isPlaying: false
 property real length: 10
}
'''
HARNESS = '''import QtQuick
import Quickshell
import qs.modules.services
import qs.modules.components
import qs.config
import "modules/services/Lyrics.js" as Parser
ShellRoot {
 function findItem(item, name) {
  if (item.objectName === name) return item;
  for (const child of item.children || []) {
   const found = findItem(child, name);
   if (found) return found;
  }
  return null;
 }
 Item {
  LyricsSection { id: menuSection; width: 216 }
  LyricsSection { id: pinnedSection; width: 540; compact: true }
 }
 Timer { interval: 600; running: true; onTriggered: {
  try {
   function check(ok, message) { if (!ok) throw Error(message); }
   check(LyricsService.lines.length === 2 && LyricsService.currentLine === 0 && LyricsService.provider === 'Spotify', 'Player priority');
   check(LyricsService.hasLyrics, 'Supplied lyrics available');
   const originalFactory = LyricsService.createRequest;
   LyricsService.createRequest = () => { throw Error('Spotify-provided lyrics must not start LRCLIB'); };
   LyricsService.refresh();
   check(LyricsService.provider === 'Spotify' && LyricsService.lines.length === 2, 'Spotify lyrics retain priority');
   LyricsService.createRequest = originalFactory;
   MprisController.position = 3.5;
   check(Parser.activeLine(LyricsService.lines, 3.5) === 1, 'Seek forward');
   check(Parser.activeLine(LyricsService.lines, 0) === -1, 'Seek backward');
   const parsed = Parser.parseLrc('[offset:-500]\\n[00:01.50][00:03.00]Repeated\\n[ar:Artist]');
   check(parsed.length === 2 && parsed[0].time === 1 && parsed[1].time === 2.5, 'LRC offsets/multiple timestamps');
   LyricsService.pin('bottom', 'test');
   check(LyricsService.pinEdge === 'bottom' && LyricsService.pinScreen === 'test', 'Bottom pin');
   LyricsService.pin('top', 'test');
   check(LyricsService.pinEdge === 'top', 'Move pin');
   LyricsService.toggle('other');
   check(LyricsService.pinEdge === '', 'Shortcut closes existing pin');
   LyricsService.toggle('other');
   check(LyricsService.pinEdge === 'top' && LyricsService.pinScreen === 'other', 'Shortcut restores edge on focused screen');
   LyricsService.toggle('other');
   check(LyricsService.pinEdge === '', 'Second shortcut press closes');
   LyricsService.pinEdge = '';
   let requests = [];
   LyricsService.createRequest = () => {
    const xhr = {readyState: 0, status: 0, responseText: '', abort: () => {}, open: (method, url) => { xhr.url = url; }, setRequestHeader: (name, value) => { xhr.header = name; }, send: () => {}};
    requests.push(xhr); return xhr;
   };
   MprisController.activePlayer = {dbusName: 'test', identity: 'Spotify', metadata: {}, trackAlbum: ''};
   LyricsService.refresh();
   const old = requests[0];
   check(!!old && old.url.includes('/api/get?') && old.header === 'Lrclib-Client', 'Identified LRCLIB exact lookup');
   MprisController.trackTitle = 'Next song';
   check(!LyricsService.hasLyrics, 'Previous song hidden immediately');
   LyricsService.refresh();
   old.readyState = XMLHttpRequest.DONE; old.status = 200;
   old.responseText = JSON.stringify({plainLyrics: 'Stale'}); old.onreadystatechange();
   check(LyricsService.plain === '', 'Stale response discarded');
   const current = requests[1]; current.readyState = XMLHttpRequest.DONE; current.status = 200;
   current.responseText = JSON.stringify({plainLyrics: 'Plain lyrics'}); current.onreadystatechange();
   check(LyricsService.plain === 'Plain lyrics' && LyricsService.provider === 'LRCLIB', 'Plain fallback');
   check(LyricsService.hasLyrics, 'Plain lyrics available');
   LyricsService.refresh(); check(requests.length === 2, 'Cached result reused');
   MprisController.trackTitle = 'Missing'; LyricsService.refresh();
   const missing = requests[2]; missing.readyState = XMLHttpRequest.DONE; missing.status = 404; missing.onreadystatechange();
   check(!LyricsService.plain && requests[3].url.includes('/api/search?'), 'Exact miss starts search');
   const search = requests[3]; search.readyState = XMLHttpRequest.DONE; search.status = 200;
   search.responseText = JSON.stringify([
    {trackName: 'Missing', artistName: 'Other Artist', duration: 10, syncedLyrics: '[00:01]Wrong'},
    {trackName: 'Missing', artistName: 'Artist', albumName: 'Another release', duration: 11, syncedLyrics: '[00:01]Found via search'},
    {trackName: 'Missing', artistName: 'Artist', duration: 120, syncedLyrics: '[00:01]Wrong recording'}
   ]); search.onreadystatechange();
   check(LyricsService.provider === 'LRCLIB' && LyricsService.lines.length === 1
     && LyricsService.plain === 'Found via search', 'Search fallback selects matching synced recording');
   check(Parser.bestMatch([{trackName: 'Else', artistName: 'Artist', duration: 10, plainLyrics: 'Wrong'}], 'Missing', 'Artist', '', 10) === null, 'Unrelated title rejected');
   check(Parser.bestMatch([{trackName: 'Missing', artistName: 'Artist', duration: 100, plainLyrics: 'Wrong'}], 'Missing', 'Artist', '', 10) === null, 'Duration mismatch rejected');
   MprisController.trackTitle = 'Unavailable'; LyricsService.refresh();
   const next = requests[4]; next.readyState = XMLHttpRequest.DONE; next.status = 404; next.onreadystatechange();
   const empty = requests[5]; empty.readyState = XMLHttpRequest.DONE; empty.status = 200; empty.responseText = '[]'; empty.onreadystatechange();
   check(LyricsService.status.includes('No lyrics') && !LyricsService.hasLyrics, 'Empty search hides overlay');
   MprisController.trackTitle = 'Rate limited'; LyricsService.refresh();
   const limited = requests[6]; limited.readyState = XMLHttpRequest.DONE; limited.status = 429; limited.onreadystatechange();
   check(!LyricsService.request && LyricsService.status.includes('busy') && requests.length === 7, 'No automatic retries on rate limit');
   MprisController.length = 4000; MprisController.trackTitle = 'Long recording'; LyricsService.refresh();
   check(!requests[7].url.includes('&duration='), 'Out-of-range API duration omitted');
   LyricsService.cancel();
   LyricsService.apply('', 'LRCLIB', true);
   check(LyricsService.status.includes('Instrumental') && !LyricsService.hasLyrics, 'Instrumental state');
   LyricsService.apply('[00:01.00]   ', 'Player', false);
   check(!LyricsService.hasLyrics, 'Empty timed lyrics hidden');
   LyricsService.pin('bottom', 'test');
   LyricsService.apply('Lyrics return', 'Player', false);
   check(LyricsService.hasLyrics && LyricsService.pinEdge === 'bottom', 'Pin retained when lyrics return');
   const label = findItem(pinnedSection, 'lyrics-text');
   check(!!label, 'Shared lyrics label exists');
   Config.theme.font = 'monospace'; Config.theme.fontSize = 19;
   check(label.font.family === Config.theme.font && label.font.pixelSize === 22
     && label.renderType === Text.NativeRendering, 'Lyrics follow shell font and rendering');
   console.log('PASS: lyrics parsing, priority, fallback, cache, stale requests, seeking and pin controls'); idleCheck.start();
  } catch (error) { console.error(error); Qt.exit(1); }
 } }
 Timer { id: idleCheck; interval: 3300; repeat: true; property int phase: 0
 onTriggered: {
  try {
   if (phase === 0) {
    if (pinnedSection.controlsVisible || pinnedSection.backgroundOpacity !== 0 || !menuSection.controlsVisible)
     throw Error('Idle view must hide chrome; menu must remain usable');
    const backing = findItem(pinnedSection, 'idle-lyrics-background');
    if (!backing || !backing.visible || backing.backgroundOpacity <= 0 || backing.backgroundOpacity >= 1)
     throw Error('Idle lyrics must retain a subtle themed background');
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

ANIMATION_HARNESS = '''import QtQuick
import QtQuick.Window
import Quickshell
import qs.modules.services
import qs.modules.components
import qs.modules.theme
import qs.config
ShellRoot {
 function findItem(item, name) {
  if (item.objectName === name) return item;
  for (const child of item.children || []) { const found = findItem(child, name); if (found) return found; }
  return null;
 }
 Window { visible: true; width: 420; height: 210; LyricsViewport { id: view; anchors.fill: parent } }
 Timer { interval: 400; running: true; repeat: true; property int phase: 0; property real initialY: 0
 onTriggered: {
  try {
   if (phase === 0) {
    Config.theme.animDuration = 300;
    LyricsService.apply('[00:00]First line\\n[00:02]Second line\\n[00:04]Current third line\\n[00:06]Fourth line\\n[00:08]Fifth line', 'Test', false);
    MprisController.position = 0; phase++; return;
   }
   if (phase === 1) {
    initialY = view.followPosition;
    MprisController.position = 4.5;
    interval = 40; phase++; return;
   }
   if (phase === 2) {
    if (!view.animating) throw Error('Scrolling animation did not start');
    interval = 600; phase++; return;
   }
   if (phase === 3) {
    const row = findItem(view, 'lyric-row-2');
    const label = findItem(view, 'lyric-line-2');
    if (!row || !row.current || view.followPosition <= initialY || view.animating || label.color.toString() !== Colors.primary.toString())
     throw Error('Forward scroll/highlight did not settle');
    view.browsing = true;
    initialY = view.followPosition;
    MprisController.position = 8.5; phase++; return;
   }
   if (phase === 4) {
    if (view.followPosition !== initialY) throw Error('Auto-follow interrupted manual browsing');
    view.browsing = false;
    Config.theme.animDuration = 0;
    MprisController.position = 0;
    interval = 80; phase++; return;
   }
   if (phase === 5) {
    if (view.animating || view.followPosition >= initialY || !findItem(view, 'lyric-row-0').current)
     throw Error('Backward seek or reduced motion failed');
    LyricsService.apply('Unsynced lyrics stay scrollable', 'Test', false); phase++; return;
   }
   if (view.synced || !LyricsService.estimated || !view.followsPlayback
     || !findItem(view, 'lyrics-text').visible || !view.hasRows)
     throw Error('Untimed lyrics with a duration must use approximate playback following');
   console.log('PASS: animated forward scroll, row highlighting, manual browsing, backward seek and reduced motion'); Qt.quit();
  } catch (error) { console.error(error); Qt.exit(1); }
 } }
}
'''

@unittest.skipUnless(shutil.which('quickshell'), 'Quickshell required')
class Lyrics(unittest.TestCase):
    def test_lyrics(self):
        self.run_harness(HARNESS)

    def test_animated_rows(self):
        self.run_harness(ANIMATION_HARNESS)

    def run_harness(self, harness):
        with tempfile.TemporaryDirectory(prefix='lyrics-test-') as directory:
            root = Path(directory)
            for name in ('modules', 'config', 'assets'):
                shutil.copytree(APP / name, root / name)
            (root / 'modules/services/MprisController.qml').write_text(PLAYER)
            (root / 'shell.qml').write_text(harness)
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
