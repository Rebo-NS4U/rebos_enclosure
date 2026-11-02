pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import qs.modules.components
import qs.modules.theme

PanelWindow {
    id: overlay

    required property bool offered
    required property string buttonLabel
    required property string destination
    required property string outputName
    property var playerPosition: [0, 0]
    property var playerSize: [0, 0]
    property bool fullscreen: true
    signal activated()

    screen: Quickshell.screens.find(value => value.name === outputName) ?? Quickshell.screens[0]
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    // Keep the surface mapped, with input restricted to the visible button.
    visible: true
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "rebos_shell-playback-next"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    mask: Region { item: overlay.offered ? nextCard : null }

    readonly property real cardX: nextCard.x
    readonly property real cardY: nextCard.y
    readonly property real cardWidth: nextCard.width
    readonly property real cardHeight: nextCard.height

    StyledRect {
        id: nextCard
        visible: overlay.offered
        width: Math.min(360, overlay.width - 48)
        height: content.implicitHeight + 28
        x: Math.max(12, overlay.width - width - 24)
        y: Math.max(12, overlay.height - height - 24)
        variant: pointer.containsMouse ? "primary" : "bg"
        backgroundOpacity: 0.96
        radius: Styling.radius(12)
        border.width: 1
        border.color: Colors.primary
        Accessible.role: Accessible.Button
        Accessible.name: overlay.buttonLabel + ": " + overlay.destination
        Accessible.onPressAction: overlay.activated()

        ColumnLayout {
            id: content
            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 18 }
            spacing: 5
            StyledText {
                text: overlay.buttonLabel + "  →"
                color: pointer.containsMouse ? Colors.overPrimary : Colors.overSurface
                font.bold: true
                font.pixelSize: Styling.fontSize(2)
            }
            StyledText {
                text: overlay.destination
                Layout.fillWidth: true
                maximumLineCount: 2
                wrapMode: Text.Wrap
                elide: Text.ElideRight
                color: pointer.containsMouse ? Colors.overPrimary : Colors.overSurfaceVariant
            }
        }
        MouseArea {
            id: pointer
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: overlay.activated()
        }
    }
}
