"""Exercise cue scheduling and spring follow with real offscreen QML."""
import unittest
import shutil
import test_lyrics as fixtures

CLOCK = '''import QtQuick
import Quickshell
import qs.modules.services
ShellRoot {
 LyricsClock {
  id: clock
  enabled: true
  lines: [{time: 0, text: 'First'}, {time: 0.8, text: 'Second'}, {time: 2, text: 'Third'}]
 }
 Timer { interval: 80; running: true; repeat: true; property int phase: 0
  onTriggered: {
   try {
    function check(ok, message) { if (!ok) throw Error(message); }
    if (phase === 0) {
     clock.position = 0.6;
     check(clock.activeIndex === 0 && clock.followIndex === 0, 'Before lead-in');
     clock.position = 0.65;
     check(clock.activeIndex === 0 && clock.followIndex === 1, 'Center early without early highlight');
     clock.playing = true; interval = 230; phase++; return;
    }
    if (phase === 1) {
     check(clock.activeIndex === 1, 'Cue timer must advance without player polling');
     clock.position = 0.9; clock.playing = false;
     interval = 250; phase++; return;
    }
    if (phase === 2) {
     check(clock.activeIndex === 1 && Math.abs(clock.currentTime() - 0.9) < 0.001, 'Paused clock must freeze');
     clock.position = 2.5;
     check(clock.activeIndex === 2, 'Forward seek');
     clock.position = 0;
     check(clock.activeIndex === 0, 'Backward seek');
     clock.position = 0.5; clock.rate = 2; clock.playing = true;
     interval = 220; phase++; return;
    }
    if (phase === 3) {
     check(clock.activeIndex === 1, 'Playback rate respected');
     clock.playing = false; clock.position = 0;
     clock.lines = [{time: 4, text: 'New song'}]; clock.trackKey = 'new';
     check(clock.activeIndex === -1 && clock.followIndex === -1, 'New song must clear old cues');
     clock.lines = [];
     check(clock.activeIndex === -1 && clock.followIndex === -1, 'Untimed lyrics must not invent timing');
     console.log('PASS: early centering, exact cues, pause, rate, seeks and track replacement'); Qt.quit();
    }
   } catch(error) { console.error(error); Qt.exit(1); }
  }
 }
}
'''

# Existing animation harness also verifies the actual themed viewport and reduced motion.
VIEW = fixtures.ANIMATION_HARNESS.replace(
    "view.browsing = false;\n    Config.theme.animDuration = 0;",
    """const follow = findItem(view, 'lyrics-follow-playback');
    if (!follow || !follow.visible) throw Error('Missing follow playback control');
    view.resume();
    if (view.browsing || follow.visible) throw Error('Follow playback did not resume');
    Config.theme.animDuration = 0;""")

TEXT_ONLY = '''import QtQuick
import QtQuick.Window
import Quickshell
import qs.modules.services
import qs.modules.components
ShellRoot {
 function findItem(item, name) {
  if (item.objectName === name) return item;
  for (const child of item.children || []) { const found = findItem(child, name); if (found) return found; }
  return null;
 }
 Window { visible: true; width: 420; height: 360; LyricsSection { id: section; anchors.fill: parent } }
 Timer { interval: 400; running: true; repeat: true; property int phase: 0; property real startY: 0
  onTriggered: {
   try {
    const view = findItem(section, 'lyrics-viewport');
    function check(ok, message) { if (!ok) throw Error(message); }
    if (phase === 0) {
     MprisController.length = 1.6;
     MprisController.position = 0;
     MprisController.activePlayer = {dbusName:'test', identity:'Spotify', metadata:{'xesam:asText':'One\\nTwo\\nThree\\nFour'}, trackAlbum:''};
     LyricsService.createRequest = () => ({open:()=>{},setRequestHeader:()=>{},send:()=>{},abort:()=>{}});
     LyricsService.refresh(); phase++; return;
    }
    if (phase === 1) {
     check(!view.followsPlayback && !view.synced && !section.visible && section.implicitHeight === 0, 'Plain source must hide the section');
     check(!LyricsService.hasLyrics && !view.hasRows && LyricsService.viewers > 0, 'Hidden section must retain lookup demand without showing text');
     startY = view.followPosition;
     MprisController.isPlaying = true; interval = 800; phase++; return;
    }
    if (phase === 2) {
     check(LyricsService.currentLine === -1 && view.followPosition === startY, 'Hidden plain lyrics must not scroll or highlight during playback');
     MprisController.position = 0.5; MprisController.isPlaying = false;
     interval = 400; phase++; return;
    }
    if (phase === 3) {
     check(LyricsService.currentLine === -1, 'Plain lyrics must not gain timing on pause');
     MprisController.length = 0;
     check(!view.followsPlayback, 'Unknown duration must remain manual');
     LyricsService.apply('[00:00]Exact\\n[00:02]Timed', 'Test', false);
     check(view.synced && section.visible && section.implicitHeight > 0 && LyricsService.displayLines[1].time === 2, 'Timed lyrics must restore the section automatically');
     console.log('PASS: text-only lyrics hidden; real timestamps restore the section and following'); Qt.quit();
    }
   } catch(error) { console.error(error); Qt.exit(1); }
  }
 }
}
'''

UPGRADE = '''import QtQuick
import Quickshell
import qs.modules.services
ShellRoot {
 property var requests: []
 Timer { interval: 400; running: true; repeat: true; property int phase: 0
  onTriggered: {
   try {
    function check(ok, message) { if (!ok) throw Error(message); }
    if (phase === 0) {
     LyricsService.createRequest = () => {
      const xhr = {readyState:0,status:0,responseText:'',open:()=>{},setRequestHeader:()=>{},send:()=>{},abort:()=>{}};
      requests.push(xhr); return xhr;
     };
     LyricsService.viewers = 1;
     MprisController.activePlayer = {dbusName:'test',identity:'Spotify',metadata:{'xesam:asText':'Plain source'},trackAlbum:''};
     LyricsService.refresh(); phase++; return;
    }
    if (phase === 1) {
     check(LyricsService.plain === 'Plain source' && LyricsService.displayLines.length === 0 && requests.length > 0, 'Keep plain source while seeking timing');
     const xhr = requests[requests.length - 1]; xhr.status = 200; xhr.readyState = XMLHttpRequest.DONE;
     xhr.responseText = JSON.stringify({plainLyrics:'Untimed exact match'}); xhr.onreadystatechange();
     check(LyricsService.plain === 'Plain source' && LyricsService.request, 'Untimed exact match must continue to timed search');
     const search = requests[requests.length - 1]; search.status = 200; search.readyState = XMLHttpRequest.DONE;
     search.responseText = JSON.stringify([{trackName:'Test',artistName:'Artist',duration:10,syncedLyrics:'[00:01]Timed fallback'}]); search.onreadystatechange();
     check(LyricsService.provider === 'LRCLIB' && LyricsService.lines[0].time === 1, 'Timed search must enable exact following');
     console.log('PASS: plain provider preserved while timed fallback is found'); Qt.quit();
    }
   } catch(error) { console.error(error); Qt.exit(1); }
  }
 }
}
'''


@unittest.skipUnless(shutil.which('quickshell'), 'Quickshell required')
class Timing(unittest.TestCase):
    def test_text_only_hidden(self):
        fixtures.Lyrics.run_harness(self, TEXT_ONLY)

    def test_timed_upgrade(self):
        fixtures.Lyrics.run_harness(self, UPGRADE)

    def test_clock(self):
        fixtures.Lyrics.run_harness(self, CLOCK)

    def test_spring_and_resume(self):
        fixtures.Lyrics.run_harness(self, VIEW)
