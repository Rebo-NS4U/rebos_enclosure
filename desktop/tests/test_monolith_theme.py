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
import Quickshell
import qs.modules.components
ShellRoot {
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
  StyledRect { id: canopy; width:500; height:240; variant:"bg"; styleOverride:"canopy" }
  StyledRect { id: canopyPane; width:220; height:130; variant:"pane"; styleOverride:"canopy" }
  StyledRect { id: canopyBar; width:580; height:40; variant:"bar"; barSurface:true; styleOverride:"canopy" }
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
   if (!hasMarks(canopy, 195, 70, 125, 95) || !hasMarks(canopy, 0, 165, 145, 74))
    throw Error("Missing Canopy foliage across the window");
   if (!hasMarks(canopyPane, 82, 35, 70, 63)) throw Error("Missing nested foliage");
   if (!hasMarks(canopyBar, 0, 0, 120, 39) || hasMarks(canopyBar, 250, 0, 80, 39))
    throw Error("Compact Canopy must frame the bar center");
   console.log("MATERIAL_RENDER_OK");
   Qt.quit();
  } catch (e) { console.error(e); Qt.exit(1); } } }
}''')
                self.assertEqual(status, 0, output[-6000:])
                self.assertIn('MATERIAL_RENDER_OK', output)
                for error in ('ReferenceError', 'TypeError', 'QML StyledRect: SyntaxError', 'Error loading QML', 'Unable to assign'):
                    self.assertNotIn(error, output)

    def test_settings_uses_assistant_sidebar_slate(self):
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
    if (!slate || !slate.outer || slate.wideSlate)
     throw Error("Settings must use the assistant sidebar's compact Monolith slate");
    Config.theme.shellStyle = "blueprint";
    if (loader.item.barSurface)
     throw Error("Blueprint must use the standard Settings surface");
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
