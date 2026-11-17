"""Render obsidian at panel, bar and inset sizes in every installed app."""
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
 FloatingWindow { visible:true; implicitWidth:640; implicitHeight:480
  Column {
   StyledRect { width:600; height:260; barSurface:true; variant:"bg"; styleOverride:"monolith" }
   StyledRect { width:500; height:200; variant:"popup"; styleOverride:"monolith" }
   StyledRect { width:200; height:80; variant:"bg"; styleOverride:"monolith" }
   StyledRect { width:220; height:42; variant:"bg"; materialPreview:true; styleOverride:"monolith" }
   StyledRect { width:600; height:36; variant:"bar"; styleOverride:"monolith" }
   StyledRect { width:200; height:80; variant:"internalbg"; styleOverride:"monolith" }
   StyledRect { width:24; height:24; variant:"focus"; styleOverride:"monolith" }
  }
 }
 Timer { interval:400; running:true; onTriggered: { console.log("OBSIDIAN_RENDER_OK"); Qt.quit(); } }
}''')
                self.assertEqual(status, 0, output[-6000:])
                self.assertIn('OBSIDIAN_RENDER_OK', output)
                for error in ('ReferenceError', 'TypeError', 'QML StyledRect: SyntaxError', 'Error loading QML', 'Unable to assign'):
                    self.assertNotIn(error, output)
