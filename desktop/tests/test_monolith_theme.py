"""Check Monolith’s window-wide slate pattern and compact surfaces in each app."""
import shutil
import unittest
from test_visual_polish import run_qml, ROOT


@unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
class MonolithThemeTests(unittest.TestCase):
    def test_material_renders_across_apps(self):
        for app in ('shell', 'assistant', 'media/ui'):
            with self.subTest(app=app):
                status, output = run_qml(ROOT / 'system/apps' / app, '''import QtQuick
import Quickshell
import qs.modules.components
ShellRoot {
 function decoration(item) {
  if (item.objectName === "surface-edge-canvas") return item;
  for (const child of item.children || []) {
   const found = decoration(child);
   if (found) return found;
  }
  return null;
 }
 function hasMarks(surface, x, y, w, h) {
  const canvas = decoration(surface);
  if (!canvas) throw Error("Missing Monolith canvas");
  const rgba = canvas.getContext("2d").getImageData(x, y, w, h).data;
  for (let i = 3; i < rgba.length; i += 4) if (rgba[i] > 3) return true;
  return false;
 }
 FloatingWindow { visible:true; implicitWidth:640; implicitHeight:480
  Column {
   StyledRect { width:600; height:260; barSurface:true; variant:"bg"; styleOverride:"monolith" }
   StyledRect { id: popup; width:500; height:200; variant:"popup"; styleOverride:"monolith" }
   StyledRect { width:200; height:80; variant:"bg"; styleOverride:"monolith" }
   StyledRect { width:220; height:42; variant:"bg"; materialPreview:true; styleOverride:"monolith" }
   StyledRect { id: bar; width:600; height:36; variant:"bar"; styleOverride:"monolith" }
   StyledRect { width:200; height:80; variant:"internalbg"; styleOverride:"monolith" }
   StyledRect { width:24; height:24; variant:"focus"; styleOverride:"monolith" }
  }
 }
 Timer { interval:400; running:true; onTriggered: { try {
   if (!hasMarks(popup, 375, 0, 125, 80) || !hasMarks(popup, 170, 65, 160, 70))
    throw Error("Missing slate across the window");
   if (hasMarks(bar, 260, 8, 80, 20)) throw Error("Slate obscures compact bar");
   console.log("SLATE_RENDER_OK");
   Qt.quit();
  } catch (e) { console.error(e); Qt.exit(1); } } }
}''')
                self.assertEqual(status, 0, output[-6000:])
                self.assertIn('SLATE_RENDER_OK', output)
                for error in ('ReferenceError', 'TypeError', 'QML StyledRect: SyntaxError', 'Error loading QML', 'Unable to assign'):
                    self.assertNotIn(error, output)
