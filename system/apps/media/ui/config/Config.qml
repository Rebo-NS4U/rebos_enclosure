pragma Singleton
import QtQuick
import Quickshell
import qs.modules.theme
import "defaults/theme.js" as Defaults
Singleton {
 readonly property var theme: Defaults.data
 readonly property string defaultFont: theme.font
 readonly property int roundness: theme.roundness
 readonly property int animDuration: theme.animDuration
 function resolveColor(value): color {
  if (value === undefined || value === null || value === "") return "transparent";
  return Colors[value] !== undefined ? Colors[value] : value;
 }
}
