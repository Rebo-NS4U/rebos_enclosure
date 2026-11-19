"""Check window-wide materials and compact surfaces in each app."""
import shutil
import unittest
from test_visual_polish import run_qml, ROOT


@unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
class WindowMaterialTests(unittest.TestCase):
    def test_material_renders_across_apps(self):
        for app in ('shell', 'assistant', 'media/ui'):
            with self.subTest(app=app):
                status, output = run_qml(ROOT / 'system/apps' / app, '''import QtQuick
import QtQuick.Controls
import QtTest
import qs.modules.theme
import Quickshell
import qs.modules.components
ShellRoot {
 TestCase { id: test; when: false }
 function decoration(item) {
  if (["surface-edge-canvas", "wallpaper-theme-canvas"].includes(item.objectName)) return item;
  for (const child of item.children || []) {
   const found = decoration(child);
   if (found) return found;
  }
  return null;
 }
 function hasMarks(surface, x, y, w, h) {
  const canvas = decoration(surface);
  if (!canvas) throw Error("Missing material canvas");
  const rgba = canvas.getContext("2d").getImageData(x, y, w, h).data;
  for (let i = 3; i < rgba.length; i += 4) if (rgba[i] > 3) return true;
  return false;
 }
 FloatingWindow { visible:true; implicitWidth:640; implicitHeight:480
  StyledRect { id: metro; width:500; height:240; backgroundOpacity:0.20; variant:"popup"; styleOverride:"metropolis" }
  StyledRect { id: metroPane; width:220; height:130; variant:"pane"; styleOverride:"metropolis" }
  StyledRect { id: metroBar; width:580; height:40; variant:"bar"; styleOverride:"metropolis" }
  StyledRect { id: metroPreview; width:200; height:42; materialPreview:true; variant:"bg"; styleOverride:"metropolis" }
  StyledRect { id: canopy; width:500; height:240; variant:"bg"; styleOverride:"canopy" }
  StyledRect { id: canopyPane; width:220; height:130; variant:"pane"; styleOverride:"canopy" }
  StyledRect { id: canopyBar; width:580; height:40; variant:"bar"; barSurface:true; styleOverride:"canopy" }
  Column {
   StyledRect { id: sidebar; width:600; height:180; barSurface:true; variant:"bg"; styleOverride:"monolith" }
   StyledRect { id: popup; width:500; height:200; variant:"popup"; styleOverride:"monolith" }
   Row {
    Button {
     id: button
     width: 140; height: 36; text: "Apply"
     background: StyledRect { variant:"common"; styleOverride:"monolith" }
    }
    Button {
     id: selected
     width: 140; height: 36; text: "Selected"
     background: StyledRect { variant:"primary"; styleOverride:"monolith" }
    }
   }
   StyledRect { width:220; height:42; variant:"bg"; materialPreview:true; styleOverride:"monolith" }
   StyledRect { id: bar; width:600; height:36; variant:"bar"; styleOverride:"monolith" }
   StyledRect { width:200; height:80; variant:"internalbg"; styleOverride:"monolith" }
   StyledRect { width:24; height:24; variant:"focus"; styleOverride:"monolith" }
  }
 }
 Timer { interval:400; running:true; onTriggered: { try {
   if (!hasMarks(popup, 375, 0, 125, 80) || !hasMarks(popup, 170, 65, 160, 70))
    throw Error("Missing slate across the window");
   if (!hasMarks(sidebar, 215, 65, 155, 60)) throw Error("Missing slate across the sidebar");
   for (const surface of [button.background, selected.background]) {
    if (!hasMarks(surface, 52, 14, 41, 9)) throw Error("Missing crack across the button face");
    if (hasMarks(surface, 0, 32, 23, 4)) throw Error("Corner accent remains on button");
   }
   if (hasMarks(popup, 0, 168, 100, 32)) throw Error("Corner accent remains on window");
   if (decoration(bar)) throw Error("Slate obscures compact bar");
   if (!hasMarks(canopy, 195, 70, 125, 95) || !hasMarks(canopy, 0, 165, 145, 74))
    throw Error("Missing Canopy foliage across the window");
   if (!hasMarks(canopyPane, 82, 35, 70, 63)) throw Error("Missing nested foliage");
   if (!hasMarks(canopyBar, 0, 0, 120, 39) || hasMarks(canopyBar, 250, 0, 80, 39))
    throw Error("Compact Canopy must frame the bar center");
   if (!hasMarks(metro, 35, 82, 40, 45) || !hasMarks(metro, 370, 139, 50, 46))
    throw Error("Missing Metropolis towers on either side of the window");
   if (hasMarks(metro, 190, 40, 120, 110)) throw Error("City encroaches on the open sky");
   if (!hasMarks(metroPane, 17, 85, 18, 22) || !hasMarks(metroPreview, 15, 17, 15, 10))
    throw Error("Missing skyline on a nested pane or theme preview");
   if (!hasMarks(metroBar, 15, 20, 80, 19) || !hasMarks(metroBar, 500, 20, 60, 19)
       || hasMarks(metroBar, 180, 0, 220, 40))
    throw Error("Metropolis rooftops must frame the bar center");
   // The middle contains only the distant, translucent skyline after resizing.
   for (const width of [240, 500, 960]) {
    metro.width = width;
    test.wait(100);
    const ctx = decoration(metro).getContext("2d");
    const column = ctx.getImageData(Math.floor(width / 2), 0, 1, metro.height).data;
    if (column[column.length - 1] < 4) throw Error("Missing distant skyline at width " + width);
    for (let i = 3; i < column.length; i += 4)
     if (column[i] > 64) throw Error("Foreground crosses the central skyline at width " + width);
   }
   console.log("MATERIAL_RENDER_OK");
   Qt.quit();
  } catch (e) { console.error(e); Qt.exit(1); } } }
}''')
                self.assertEqual(status, 0, output[-6000:])
                self.assertIn('MATERIAL_RENDER_OK', output)
                for error in ('ReferenceError', 'TypeError', 'QML StyledRect: SyntaxError', 'Error loading QML', 'Unable to assign'):
                    self.assertNotIn(error, output)

    def test_settings_renders_full_monolith_cracks(self):
        status, output = run_qml(ROOT / 'system/apps/shell', '''import QtQuick
import QtTest
import Quickshell
import qs.config
import qs.modules.globals
import qs.modules.widgets.config
ShellRoot {
 SettingsWindow { id: settings }
 TestCase { id: test; when: false }
 Timer {
  interval: 400
  running: true
  onTriggered: {
   try {
    Config.theme.shellStyle = "monolith";
    GlobalStates.settingsWindowVisible = true;
    const loader = test.findChild(settings.contentItem, "settingsContentLoader");
    const slate = test.findChild(loader.item, "surface-edge-canvas");
    if (!slate)
     throw Error("Settings must use the full Monolith slate");
    test.wait(150);
    const ctx = slate.getContext("2d");
    for (const [x, y] of [[0.16, 0.52], [0.43, 0.38], [0.75, 0.12]]) {
     const pixels = ctx.getImageData(Math.floor(slate.width * x), Math.floor(slate.height * y),
         Math.floor(slate.width * 0.16), Math.floor(slate.height * 0.18)).data;
     let index = 3;
     while (index < pixels.length && pixels[index] <= 3) index += 4;
     if (index >= pixels.length)
      throw Error("Missing Monolith cracks across Settings at " + x + ", " + y);
    }
    console.log("SETTINGS_SLATE_OK");
    Qt.quit();
   } catch (error) {
    console.error(error);
    Qt.exit(1);
   }
  }
 }
}''')
        self.assertEqual(status, 0, output[-6000:])
        self.assertIn('SETTINGS_SLATE_OK', output)
