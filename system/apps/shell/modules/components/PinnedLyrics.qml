import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.modules.services
import qs.modules.globals

PanelWindow {
    id: root
    property ShellScreen targetScreen
    screen: targetScreen
    visible: LyricsService.pinEdge !== "" && LyricsService.hasLyrics && !GlobalStates.lockscreenVisible
        && (LyricsService.pinScreen === targetScreen.name
            || (!Quickshell.screens.some(s => s.name === LyricsService.pinScreen) && targetScreen === Quickshell.screens[0]))
    anchors.top: LyricsService.pinEdge === "top"
    anchors.bottom: LyricsService.pinEdge === "bottom"
    margins.top: 56
    margins.bottom: 56
    implicitWidth: Math.min(540, targetScreen.width - 32)
    implicitHeight: lyrics.implicitHeight
    color: "transparent"
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.namespace: "rebos_shell:lyrics"
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
    LyricsSection { id: lyrics; anchors.fill: parent; compact: true }
}
