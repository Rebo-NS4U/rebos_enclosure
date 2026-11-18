"""Check the shared rail in a real, isolated QML runtime."""
from pathlib import Path
import unittest
import test_lyrics

ROOT = Path(__file__).resolve().parents[2]

class StandardProgress(unittest.TestCase):
    def test_app_copies_match(self):
        paths = [ROOT / 'system/apps' / name / 'StandardProgressBar.qml' for name in (
            'shell/modules/components', 'assistant/modules/components', 'media/ui/modules/components')]
        self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
        self.assertEqual(paths[0].read_bytes(), paths[2].read_bytes())

    def test_rail_and_slider_rendering(self):
        test_lyrics.Lyrics().run_harness('''import QtQuick
import Quickshell
import qs.modules.components
ShellRoot {
 Item {
  width: 300; height: 200
  StandardProgressBar { id: rail; width: 200; value: 0.5 }
  StyledSlider { id: horizontal; width: 200; height: 32; value: 0.5 }
  StyledSlider { id: vertical; width: 32; height: 120; vertical: true; value: 0.5 }
  ThemeSlider { id: themed; width: 200; value: 0.5 }
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
   check(themed.background.children[0].height === 2, 'Theme slider uses thin shared rail');
   rail.value = 0.61;
   activeCheck.start();
  } catch(error) { console.error(error); Qt.exit(1); }
 }}
 Timer { id: activeCheck; interval: 180; onTriggered: {
  const fill = rail.children.find(child => child.objectName === 'standard-progress-fill');
  const marks = fill.children.filter(child => child.objectName === 'standard-progress-mark');
  if (marks.some(mark => !mark.visible || mark.x < 0 || mark.x + mark.width > fill.width)) {
   console.error('Moving marks must stay within the fill'); Qt.exit(1); return;
  }
  travelCheck.startX = marks[0].x;
  travelCheck.start();
 }}
 Timer { id: travelCheck; interval: 120
  property real startX: 0
  onTriggered: {
   const fill = rail.children.find(child => child.objectName === 'standard-progress-fill');
   const mark = fill.children.find(child => child.objectName === 'standard-progress-mark');
   if (rail.value !== 0.61 || Math.abs(mark.x - startX) < 1) {
    console.error('Marks must travel between value updates'); Qt.exit(1); return;
   }
   idleCheck.start();
 }}
 Timer { id: idleCheck; interval: 650; onTriggered: {
  const fill = rail.children.find(child => child.objectName === 'standard-progress-fill');
  const mark = fill.children.find(child => child.objectName === 'standard-progress-mark');
  if (mark.visible) { console.error('Pulse must settle after movement'); Qt.exit(1); return; }
  console.log('PASS: shared progress geometry, motion and slider input'); Qt.quit();
 }}
}
''')

if __name__ == '__main__': unittest.main()
