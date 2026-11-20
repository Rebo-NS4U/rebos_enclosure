pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.modules.theme
import "defaults/theme.js" as Defaults
Singleton {
 id: root
 property var savedTheme: ({})
 readonly property var theme: Object.assign({}, Defaults.data, savedTheme)
 readonly property bool lightMode: theme.lightMode
 readonly property bool oledMode: !lightMode && theme.oledMode
 // Read shell preferences without creating or rewriting personal settings.
 FileView {
  path: (Quickshell.env("XDG_CONFIG_HOME") || (Quickshell.env("HOME") + "/.config")) + "/rebos_shell/config/theme.json"
  watchChanges: true
  preload: true
  onFileChanged: reload()
  onLoaded: {
   try {
    const values = JSON.parse(text());
    if (values === null || Array.isArray(values) || typeof values !== "object")
     throw new Error("Expected a theme object");
    if (["frosted-ceramic", "suspended-film", "circuit-glass", "prism-glass", "optical-instrument"].includes(values.shellStyle))
     values.shellStyle = "guilloche";
    root.savedTheme = values;
   } catch (error) {
    console.warn("Keeping the last Streamer theme settings:", error);
   }
  }
 }
 readonly property string defaultFont: theme.font
 readonly property int roundness: theme.roundness
 readonly property int animDuration: theme.animDuration
 function resolveColor(value): color {
  if (value === undefined || value === null || value === "") return "transparent";
  return Colors[value] !== undefined ? Colors[value] : value;
 }
}
