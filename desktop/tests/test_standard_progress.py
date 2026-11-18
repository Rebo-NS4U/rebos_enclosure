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
            app_paths = paths if component == 'StandardProgressBar.qml' else paths[1:]
            source, *copies = [path.with_name(component).read_bytes() for path in app_paths]
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
  StyledSlider { id: horizontal; width: 200; height: 32; value: 0.5 }
  StyledSlider { id: vertical; width: 32; height: 120; vertical: true; value: 0.5 }
  ThemeSlider { id: themed; width: 200; value: 0.5 }
  ThemeSlider { id: themedVertical; height: 120; orientation: Qt.Vertical; value: 0.5 }
  ThemeSlider { id: themedMirrored; width: 200; value: 0.5
   LayoutMirroring.enabled: true
  }
 }
 Timer { interval: 900; running: true; onTriggered: {
  try {
   function check(ok, message) { if (!ok) throw Error(message); }
   const fill = rail.children.find(child => child.objectName === 'standard-progress-fill');
   check(!fill.gradient && Qt.colorEqual(fill.color, rail.activeColor), 'Rail has a solid active fill');
   check(fill.width === 100, 'Half progress must fill half the rail');
   const marks = fill.children.filter(child => child.objectName === 'standard-progress-mark');
   check(marks.length === 3 && marks.every(mark => !mark.visible), 'Idle rail is solid');
   check(marks[1].x - marks[0].x !== marks[2].x - marks[1].x, 'Mark spacing is uneven');
   rail.value = 0.505;
   check(rail.pulseStrength === 1 && Math.abs(fill.width - 101) < 0.01, 'Value changes wake the marks');
   rail.value = 0.5;
   const tip = fill.children.find(child => child.objectName === 'standard-progress-tip');
   check(tip.width === 4 && tip.x + tip.width === fill.width, 'Solid tip follows the filled edge');
   check(!tip.gradient && Qt.colorEqual(tip.color, rail.foregroundColor), 'Tip uses the foreground color');
   rail.value = 0.005; check(tip.width === fill.width, 'Tip fits short fills');
   rail.value = -1; check(fill.width === 0 && tip.width === 0, 'Negative values clamp');
   rail.value = 2; check(fill.width === 200, 'Overflow values clamp');
   rail.value = NaN; check(fill.width === 0, 'Nonfinite values are safe');
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
   const sliderRail = themed.background.children[0];
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
   rail.value = 0.61;
   themedVertical.playing = true;
   activeCheck.start();
  } catch(error) { console.error(error); Qt.exit(1); }
 }}
 Timer { id: activeCheck; interval: 180; onTriggered: {
  const fill = rail.children.find(child => child.objectName === 'standard-progress-fill');
  const marks = fill.children.filter(child => child.objectName === 'standard-progress-mark');
  if (marks.some(mark => !mark.visible || mark.x < 0 || mark.x + mark.width > fill.width)) {
   console.error('Moving marks must stay within the fill'); Qt.exit(1); return;
  }
  const sliderRail = themed.background.children[0];
  if (sliderRail.energy !== 0 || Math.abs(sliderRail.value - 0.8) > 0.001
          || Math.abs(themed.handle.x + themed.handle.width / 2
              - themed.background.x - sliderRail.x - sliderRail.width * sliderRail.value) > 0.01) {
   console.error('Hover and value updates keep the rail still while the thumb follows the value'); Qt.exit(1); return;
  }
  travelCheck.startX = marks[0].x;
  travelCheck.playbackPhase = themedVertical.background.children[0].phase;
  const track = horizontal.children[0].children[0].children.find(item => item.segmentCount > 0);
  travelCheck.segmentCenters = track.children.filter(item => item.wave !== undefined).map(item => item.y + item.height / 2);
  travelCheck.start();
 }}
 Timer { id: travelCheck; interval: 120
  property real startX: 0
  property real playbackPhase: 0
  property var segmentCenters: []
  onTriggered: {
   const fill = rail.children.find(child => child.objectName === 'standard-progress-fill');
   const mark = fill.children.find(child => child.objectName === 'standard-progress-mark');
   if (rail.value !== 0.61 || Math.abs(mark.x - startX) < 1) {
    console.error('Marks must travel between value updates'); Qt.exit(1); return;
   }
   const track = horizontal.children[0].children[0].children.find(item => item.segmentCount > 0);
   const verticalTrack = vertical.children[1].children[0].children.find(item => item.segmentCount > 0);
   const playbackTrack = themedVertical.background.children[0];
   if (playbackTrack.pressed || playbackTrack.energy !== 0.65 || playbackTrack.phase === playbackPhase) {
    console.error('Playback keeps a gentler ripple moving between position updates'); Qt.exit(1); return;
   }
   themedVertical.playing = false;
   const segments = track.children.filter(item => item.wave !== undefined);
   const first = segments[0];
   const last = segments[segments.length - 1];
   if (track.value !== 0.8 || verticalTrack.value !== 0.6 || verticalTrack.energy < 0.95
       || first.children[0].width !== first.width || last.children[0].width !== 0
       || segments.some(segment => segment.height !== 6 || Math.abs(segment.y + segment.height / 2 - track.height / 2) > 1.5)
       || segments.some(segment => Math.abs(segment.x + segment.width / 2 - track.filledLength) >= 64 && segment.wave !== 0)
       || !segments.some((segment, index) => Math.abs(segment.y + segment.height / 2 - segmentCenters[index]) > 0.05)) {
    console.error('Dragging creates a shallow, localized ripple with fixed track thickness'); Qt.exit(1); return;
   }
   horizontal.value = horizontal.dragPosition;
   horizontal.isDragging = false;
   vertical.value = vertical.dragPosition;
   vertical.isDragging = false;
   idleCheck.start();
 }}
 Timer { id: idleCheck; interval: 650; onTriggered: {
  const fill = rail.children.find(child => child.objectName === 'standard-progress-fill');
  const mark = fill.children.find(child => child.objectName === 'standard-progress-mark');
  const track = horizontal.children[0].children[0].children.find(item => item.segmentCount > 0);
  if (mark.visible || themedVertical.background.children[0].energy !== 0 || track.energy !== 0 || track.children[0].height !== 6) {
   console.error('Tracks must settle after movement'); Qt.exit(1); return;
  }
  Config.animDuration = 0;
  themed.value = 0.25;
  const themedTrack = themed.background.children[0];
  horizontal.isDragging = true;
  themed.playing = true;
  if (themedTrack.energy !== 0 || themedTrack.value !== 0.25 || track.energy !== 0 || track.children[0].height !== 6) {
   console.error('Motion off applies value changes immediately and keeps the track still'); Qt.exit(1); return;
  }
  const segments = themedTrack.children.filter(item => item.wave !== undefined);
  const origin = segments[9];
  themed.value = (origin.x + origin.width / 2) / themedTrack.width;
  themedTrack.energy = 1;
  const phaseOffset = 2 * Math.PI * 2 * themedTrack.pitch / 64;
  themedTrack.phase = -Math.PI / 2 + phaseOffset;
  if (segments[7].wave >= -0.3 || segments[11].wave >= -0.3) {
   console.error('The trough dips on both sides near the thumb'); Qt.exit(1); return;
  }
  themedTrack.phase += Math.PI;
  if (segments[7].wave <= 0.3 || segments[11].wave <= 0.3 || segments[0].wave !== 0 || segments[18].wave !== 0) {
   console.error('The crest rises near the thumb and the distant track stays flat'); Qt.exit(1); return;
  }
  themedTrack.phase = Math.PI / 2 + 2 * Math.PI * 6 * themedTrack.pitch / 64;
  if (segments[15].wave < 0.15) {
   console.error('The ripple reaches past the previous 40-pixel limit'); Qt.exit(1); return;
  }
  const verticalTrack = vertical.children[1].children[0].children.find(item => item.segmentCount > 0);
  for (const [rail, thumb] of [
   [track, track.parent.children[0]],
   [verticalTrack, verticalTrack.parent.children[0]],
   ...[themed, themedVertical, themedMirrored].map(slider => [slider.background.children[0], slider.handle])
  ]) {
   rail.energy = 1;
   const nearest = rail.children.filter(item => item.wave !== undefined)
    .reduce((best, item) => Math.abs(item.x + item.width / 2 - rail.filledLength)
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
