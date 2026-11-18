"""Check the shared rail in a real, isolated QML runtime."""
from pathlib import Path
import unittest
import test_lyrics

ROOT = Path(__file__).resolve().parents[2]

class StandardProgress(unittest.TestCase):
    def test_app_copies_match(self):
        paths = [ROOT / 'system/apps' / name / 'StandardProgressBar.qml' for name in (
            'shell/modules/components', 'assistant/modules/components', 'media/ui/modules/components')]
        for component in ('StandardProgressBar.qml', 'SliderTrack.qml'):
            source, *copies = [path.with_name(component).read_bytes() for path in paths[1:]]
            for copy in copies:
                self.assertEqual(source, copy)

    def test_rail_and_slider_rendering(self):
        test_lyrics.Lyrics().run_harness('''import QtQuick
import Quickshell
import qs.modules.components
import qs.config
ShellRoot {
 Item {
  width: 300; height: 200
  StandardProgressBar { id: rail; width: 200; value: 0.5 }
  StandardProgressBar { id: customHandleRail; width: 200; value: 0.5; showCursor: false; playing: false }
  StyledSlider { id: horizontal; width: 200; height: 32; value: 0.5 }
  StyledSlider { id: vertical; width: 32; height: 120; vertical: true; value: 0.5 }
  ThemeSlider { id: themed; width: 200; value: 0.5 }
  ThemeSlider { id: themedVertical; height: 120; orientation: Qt.Vertical; value: 0.5 }
  ThemeSlider { id: themedMirrored; width: 200; value: 0.5
   LayoutMirroring.enabled: true
  }
 }
 Connections {
  id: playbackMotion
  target: themedVertical.background.children[0]
  property bool easedIn: false
  property bool easedOut: false
  function onEnergyChanged() {
   if (target.energy <= 0 || target.energy >= 0.65)
    return;
   if (themedVertical.playing)
    easedIn = true;
   else
    easedOut = true;
  }
 }
 Timer { interval: 900; running: true; onTriggered: {
  try {
   function check(ok, message) { if (!ok) throw Error(message); }
   const progressTrack = rail.children[0];
   check(rail.filledLength === 100, 'Half progress must fill half the rail');
   const cursor = rail.children.find(item => item.objectName === 'progress-cursor');
   check(cursor.visible && cursor.color.toString() === "#ffffff" && cursor.x + cursor.width / 2 === rail.filledLength
    && cursor.y + cursor.height / 2 === rail.height / 2,
    'The progress cursor sits at the fill edge');
   check(!customHandleRail.children.find(item => item.objectName === 'progress-cursor').visible,
    'A caller can supply its own handle');
   const sliderRail = themed.background.children[0];
   check(progressTrack.energy === 0.65 && progressTrack.thickness === sliderRail.thickness
    && rail.height === sliderRail.thickness && progressTrack.rippleAmplitude === sliderRail.rippleAmplitude,
    'Steady progress uses the slider track thickness and playback ripple');
   rail.value = 0.61;
   check(rail.filledLength < 122 && cursor.x + cursor.width / 2 === rail.filledLength,
    'The cursor and fill ease together toward the new value');
   for (const slider of [horizontal, vertical, themed]) {
    for (const quarter of [0.25, 0.5, 0.75]) {
     for (const delta of [-0.03, -0.02, 0, 0.02, 0.03])
      check(slider.snapQuarter(quarter + delta) === quarter, 'Quarter detent includes both boundaries');
     for (const delta of [-0.031, 0.031])
      check(slider.snapQuarter(quarter + delta) === quarter + delta, 'Pointer escapes detent');
    }
    check(slider.snapQuarter(0.01) === 0.01 && slider.snapQuarter(0.99) === 0.99, 'Endpoints remain free');
   }
   horizontal.editValue(0.5); horizontal.editValue(horizontal.value + 0.01);
   check(horizontal.value === 0.51, 'Keyboard can leave detent');
   horizontal.value = 0.49; check(horizontal.value === 0.49, 'External updates remain exact');
   horizontal.editValue(2); check(horizontal.value === 1, 'Slider input clamps');
   vertical.editValue(-1); check(vertical.value === 0, 'Vertical slider input clamps');
   check(sliderRail.segmentCount > 10 && sliderRail.energy === 0, 'Theme slider starts with an idle segmented track');
   sliderRail.hovered = true;
   themed.value = 0.8;
   check(sliderRail.value < themed.position, 'Programmatic slider changes ease toward their value');
   horizontal.dragPosition = 0.8;
   horizontal.isDragging = true;
   vertical.dragPosition = 0.6;
   vertical.isDragging = true;
   check(horizontal.animatedProgress === 0.8 && vertical.animatedProgress === 0.6,
    'Dragging tracks the value immediately in both orientations');
   themedVertical.playing = true;
   activeCheck.start();
  } catch(error) { console.error(error); Qt.exit(1); }
 }}
 Timer { id: activeCheck; interval: 180; onTriggered: {
  const progressTrack = rail.children[0];
  const segments = progressTrack.children.filter(item => item.wave !== undefined);
  const cursor = rail.children.find(item => item.objectName === 'progress-cursor');
  if (Math.abs(rail.filledLength - 122) > 0.01 || progressTrack.energy <= 0
      || Math.abs(cursor.x + cursor.width / 2 - rail.filledLength) > 0.01
      || segments.some(item => item.x + item.width > rail.filledLength && item.wave !== 0)
      || !segments.some(item => item.wave !== 0)) {
   console.error('Progress settles at its value and ripples only on the filled track'); Qt.exit(1); return;
  }
  const sliderRail = themed.background.children[0];
  if (sliderRail.energy !== 0 || Math.abs(sliderRail.value - 0.8) > 0.001
          || Math.abs(themed.handle.x + themed.handle.width / 2
              - themed.background.x - sliderRail.x - sliderRail.width * sliderRail.value) > 0.01) {
   console.error('Hover and value updates keep the rail still while the thumb follows the value'); Qt.exit(1); return;
  }
  travelCheck.progressPhase = progressTrack.phase;
  travelCheck.playbackPhase = themedVertical.background.children[0].phase;
  const track = horizontal.children[0].children[0].children.find(item => item.segmentCount > 0);
  travelCheck.segmentCenters = track.children.filter(item => item.wave !== undefined).map(item => item.y + item.height / 2);
  travelCheck.start();
 }}
 Timer { id: travelCheck; interval: 120
  property real progressPhase: 0
  property real playbackPhase: 0
  property var segmentCenters: []
  onTriggered: {
   if (rail.value !== 0.61 || rail.children[0].phase === progressPhase) {
    console.error('The progress ripple travels between value updates'); Qt.exit(1); return;
   }
   const track = horizontal.children[0].children[0].children.find(item => item.segmentCount > 0);
   const verticalTrack = vertical.children[1].children[0].children.find(item => item.segmentCount > 0);
   const playbackTrack = themedVertical.background.children[0];
   if (!playbackMotion.easedIn || playbackTrack.pressed || playbackTrack.energy !== 0.65 || playbackTrack.phase === playbackPhase) {
    console.error('Playback keeps a gentler ripple moving between position updates'); Qt.exit(1); return;
   }
   themedVertical.playing = false;
   rail.playing = false;
   const segments = track.children.filter(item => item.wave !== undefined);
   const first = segments[0];
   const last = segments[segments.length - 1];
   if (track.value !== 0.8 || verticalTrack.value !== 0.6 || verticalTrack.energy < 0.95
       || first.children[0].width !== first.width || last.children[0].width !== 0
       || segments.some(segment => segment.height !== 6 || Math.abs(segment.y + segment.height / 2 - track.height / 2) > 1.5)
       || segments.some(segment => segment.x + segment.width > track.filledLength && segment.wave !== 0)
       || !segments.some((segment, index) => Math.abs(segment.y + segment.height / 2 - segmentCenters[index]) > 0.05)) {
    console.error('Dragging creates a shallow ripple only on the filled track'); Qt.exit(1); return;
   }
   horizontal.value = horizontal.dragPosition;
   horizontal.isDragging = false;
   vertical.value = vertical.dragPosition;
   vertical.isDragging = false;
   idleCheck.start();
 }}
 Timer { id: idleCheck; interval: 650; onTriggered: {
  const track = horizontal.children[0].children[0].children.find(item => item.segmentCount > 0);
  if (!playbackMotion.easedOut || rail.children[0].energy !== 0 || themedVertical.background.children[0].energy !== 0 || track.energy !== 0 || track.children[0].height !== 6) {
   console.error('Tracks must settle after movement'); Qt.exit(1); return;
  }
  Config.animDuration = 0;
  const cursor = rail.children.find(item => item.objectName === 'progress-cursor');
  for (const [value, width] of [[0.25, 50], [-1, 0], [2, 200], [NaN, 0]]) {
   rail.value = value;
   const expectedCursorX = Math.max(0, Math.min(rail.width - cursor.width, width - cursor.width / 2));
   if (rail.filledLength !== width || rail.children[0].energy !== 0 || cursor.x !== expectedCursorX) {
    console.error('Reduced motion progress is immediate and clamped'); Qt.exit(1); return;
   }
  }
  themed.value = 0.25;
  const themedTrack = themed.background.children[0];
  horizontal.isDragging = true;
  themed.playing = true;
  if (themedTrack.energy !== 0 || themedTrack.value !== 0.25 || track.energy !== 0 || track.children[0].height !== 6) {
   console.error('Motion off applies value changes immediately and keeps the track still'); Qt.exit(1); return;
  }
  themed.value = 0.75;
  const verticalTrack = vertical.children[1].children[0].children.find(item => item.segmentCount > 0);
  for (const [rail, thumb] of [
   [track, track.parent.children[0]],
   [verticalTrack, verticalTrack.parent.children[0]],
   ...[themed, themedVertical, themedMirrored].map(slider => [slider.background.children[0], slider.handle])
  ]) {
   rail.energy = 1;
   const segments = rail.children.filter(item => item.wave !== undefined);
   const first = segments[0];
   const distance = rail.filledLength - first.x - first.width / 2;
   rail.phase = Math.PI / 2 + 2 * Math.PI * distance / rail.rippleWavelength;
   if (first.wave < 0.95 || segments.some(item => item.x + item.width > rail.filledLength && item.wave !== 0)) {
    console.error('The ripple runs through the filled track and stops at the thumb'); Qt.exit(1); return;
   }
   const nearest = segments.reduce((best, item) => Math.abs(item.x + item.width / 2 - rail.filledLength)
     < Math.abs(best.x + best.width / 2 - rail.filledLength) ? item : best);
   for (const phase of [-Math.PI / 2, Math.PI / 2]) {
    rail.phase = phase;
    const center = thumb.mapToItem(rail, thumb.width / 2, thumb.height / 2);
    if (Math.abs(center.x - rail.filledLength) > 0.01
        || Math.abs(center.y - rail.height / 2) > 0.01
        || Math.abs(nearest.y + nearest.height / 2 - center.y) > 0.01) {
     console.error('The track and stationary thumb must meet at the current value', center,
                   rail.filledLength, rail.rotation);
     Qt.exit(1); return;
    }
   }
  }
  console.log('PASS: shared progress geometry, motion and slider input'); Qt.quit();
 }}
}
''')

if __name__ == '__main__': unittest.main()
