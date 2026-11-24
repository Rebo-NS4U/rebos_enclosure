pragma ComponentBehavior: Bound

import QtQuick
import qs.config
import QtQuick.Controls
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
    property bool introAvailable: false
    signal skipIntro()
    signal activated()

    screen: Quickshell.screens.find(value => value.name === outputName) ?? Quickshell.screens[0]
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    // Keep the surface mapped, with pointer input restricted to the visible button.
    visible: true
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "rebos_shell-playback-next"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: offered ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
    mask: Region {
        item: overlay.offered ? nextCard : null
        regions: [Region { item: overlay.introAvailable ? introButton : null }]
    }

    readonly property real cardX: nextCard.x
    readonly property real cardY: nextCard.y
    readonly property real cardWidth: nextCard.width
    readonly property real cardHeight: nextCard.height

    Button {
        id: introButton
        visible: overlay.introAvailable
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 90 }
        text: "Skip Intro"
        hoverEnabled: true
        padding: 8
        contentItem: StyledText {
            text: introButton.text
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: StyledRect {
            variant: introButton.hovered ? "focus" : "bg"
            radius: Styling.radius(8)
        }
        onClicked: overlay.skipIntro()
    }

    StyledRect {
        id: nextCard
        visible: overlay.offered
        focus: overlay.offered
        Keys.onPressed: event => {
            if (overlay.offered && !event.isAutoRepeat
                    && (event.key === Qt.Key_Return || event.key === Qt.Key_Enter)) {
                overlay.activated();
                event.accepted = true;
            }
        }
        width: Math.min(360, overlay.width - 48)
        height: content.implicitHeight + 28
        x: Math.max(12, overlay.width - width - 24)
        y: Math.max(12, overlay.height - height - 48)
        variant: pointer.containsMouse ? "primary" : "bg"
        backgroundOpacity: 0.96
        radius: Styling.radius(12)
        border.width: Config.controlBorderWidth
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
