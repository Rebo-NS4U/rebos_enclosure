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


@unittest.skipUnless(shutil.which('quickshell'), 'Quickshell required')
class Timing(unittest.TestCase):
    def test_clock(self):
        fixtures.Lyrics.run_harness(self, CLOCK)

    def test_spring_and_resume(self):
        fixtures.Lyrics.run_harness(self, VIEW)
