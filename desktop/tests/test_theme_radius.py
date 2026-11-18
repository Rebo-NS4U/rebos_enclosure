"""Validate shared compositor corners, including square and changed themes."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts'
sys.path.insert(0, str(SCRIPTS))
from apply_desktop_palette import apply_niri_theme

class ThemeRadiusTests(unittest.TestCase):
    def test_spotify_stays_opaque_with_transparent_theme(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            apply_niri_theme(dict(primary='#112233', secondary='#223344',
                                 outlineVariant='#334455', opacity=0.68), home)
            rules = (home / '.cache/rebos_shell/niri-colors.kdl').read_text()
            spotify = next(block for block in rules.split('window-rule {') if 'Spotify' in block)
            self.assertIn('opacity 1.0', spotify)
            self.assertNotIn('dolphin', spotify)
            self.assertIn('opacity 0.68', rules)

    def test_generated_window_and_popup_corners_follow_theme(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            theme = home / '.config/enclosure/shell/config/theme.json'
            theme.parent.mkdir(parents=True)
            palette = dict(primary='#112233', secondary='#223344', outlineVariant='#334455')
            for value, expected in [(16,16), (0,0), (24,24), (100,40), ('bad',16)]:
                theme.write_text(json.dumps({'roundness':value}))
                apply_niri_theme(palette, home)
                css = (home / '.cache/rebos_shell/niri-colors.kdl').read_text()
                self.assertEqual(css.count(f'geometry-corner-radius {expected}\n'), 2)
                self.assertIn('clip-to-geometry true', css)
                self.assertIn('active-color "#112233"', css)
            theme.unlink()
            apply_niri_theme(palette, home)
            self.assertIn('geometry-corner-radius 16', (home / '.cache/rebos_shell/niri-colors.kdl').read_text())

class ThemeDecorationCornerTests(unittest.TestCase):
    def test_live_radius_updates_reach_all_theme_decorations(self):
        import os
        import shutil
        import subprocess
        if not shutil.which('qs'):
            self.skipTest('Requires Quickshell')
        app = SCRIPTS.parent
        with tempfile.TemporaryDirectory(prefix='vault-radius-') as directory:
            root = Path(directory)
            for name in ('modules', 'config', 'assets', 'scripts', 'version'):
                (root / name).symlink_to(app / name)
            (root / 'runtime').mkdir(mode=0o700)
            (root / 'shell.qml').write_text('''import QtQuick
import QtQuick.Window
import Quickshell
import qs.config
import qs.modules.components
ShellRoot {
 function decoration(node) {
  if (["structural-glass-canvas","classic-glass-canvas","drafting-corner-canvas","surface-edge-canvas","wallpaper-theme-canvas","clear-glass-canvas"].includes(node.objectName)) return node;
  for (const child of node.children || []) { const result = decoration(child); if (result) return result; }
  return null;
 }
 Window { visible: true; width: 300; height: 240
  StyledRect { id: orbitalPane; width: 256; height: 129; variant: "pane"; styleOverride: "orbital"; radius: 16 }
  Grid { columns: 3; spacing: 2
   Repeater { id: cards
    model: ["glass-vault","radar-station","suspended-film","monolith","blueprint","terminal-hardware","frosted","colorful","clear-glass","canopy","orbital","metropolis"]
    StyledRect { required property string modelData; width:96; height:72; variant:"bg"; styleOverride:modelData; animateRadius:false }
   }
  }
 }
 Timer {
  property int step: 0
  interval: 150; running: true; repeat: true
  onTriggered: {
   const values = [0,16,40,100];
   if (step === values.length) { Qt.quit(); return; }
   if (step === 1) {
    const ctx = decoration(orbitalPane).getContext("2d");
    const interiorStar = ctx.getImageData(41, 23, 1, 1).data[3];
    const clippedCross = ctx.getImageData(204, 124, 1, 1).data[3];
    if (!(interiorStar > 0) || clippedCross !== 0)
     console.error("THEME_RADIUS_FAILED orbital pane star clipping", interiorStar, clippedCross);
   }
   const expected = values[step++];
   Config.theme.roundness = expected;
   Qt.callLater(() => {
    for (let i=0;i<cards.count;i++) {
     const panel=cards.itemAt(i), canvas=decoration(panel);
     if (panel.radius !== expected || (canvas && canvas.cornerRadius !== Math.min(expected,36))) {
      console.error("THEME_RADIUS_FAILED",panel.modelData,expected,panel.radius,canvas ? canvas.cornerRadius : "native"); Qt.quit();
     } else console.log("THEME_RADIUS_OK",panel.modelData,expected);
     panel.topLeftRadius = 0; panel.topRightRadius = 0;
     const curves = [];
     const ctx = {beginPath:()=>{}, moveTo:()=>{}, lineTo:()=>{},
                  quadraticCurveTo:(...args)=>curves.push(args)};
     panel.traceThemeFrame(ctx, 3);
     const lower = Math.max(0, Math.min(expected,36)-3);
     if (curves[0][3] !== 3 || curves[3][2] !== 3 ||
         curves[1][2] !== 93-lower || curves[2][3] !== 69-lower) {
      console.error("THEME_RADIUS_FAILED attached frame",panel.modelData,expected,JSON.stringify(curves));
     }
     panel.topLeftRadius = Qt.binding(() => panel.radius);
     panel.topRightRadius = Qt.binding(() => panel.radius);
    }
   });
  }
 }
}''')
            env = dict(os.environ, HOME=directory, XDG_RUNTIME_DIR=str(root / 'runtime'),
                       QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='basic')
            for key in ('WAYLAND_DISPLAY', 'DISPLAY', 'DBUS_SESSION_BUS_ADDRESS', 'NIRI_SOCKET'):
                env.pop(key, None)
            result = subprocess.run(['qs', '-p', str(root / 'shell.qml')], env=env,
                                    text=True, capture_output=True, timeout=15)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertNotIn('THEME_RADIUS_FAILED', output)
            self.assertEqual(output.count('THEME_RADIUS_OK'), 48, output)
            for error in ('ReferenceError', 'TypeError', 'Unable to assign', 'Cannot assign'):
                self.assertNotIn(error, output)
