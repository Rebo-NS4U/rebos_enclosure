pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
Singleton {
 id: root
 property bool lockscreenVisible: false
 Process {
  id: probe
  command: ["loginctl", "show-session", Quickshell.env("XDG_SESSION_ID") || "self", "-p", "LockedHint", "--value"]
  running: true
  stdout: StdioCollector { onStreamFinished: root.lockscreenVisible = text.trim() === "yes" }
 }
 Timer { interval: 1000; running: true; repeat: true; onTriggered: probe.running = true }
}
