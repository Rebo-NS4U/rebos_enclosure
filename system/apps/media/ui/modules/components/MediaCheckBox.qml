import QtQuick
import QtQuick.Controls
import qs.config
import qs.modules.theme

CheckBox {
    id: control
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    implicitHeight: Math.max(36, label.implicitHeight + 12)
    implicitWidth: label.implicitWidth + leftPadding + rightPadding
    leftPadding: 36
    rightPadding: 8
    opacity: enabled ? 1 : 0.45
    Accessible.name: text
    indicator: Rectangle {
        objectName: "media-check-indicator"
        x: 6
        y: (control.height - height) / 2
        width: 22; height: 22
        radius: Math.min(6, Config.roundness)
        color: control.checked ? Colors.primary : Colors.surface
        border.width: 3
        border.color: control.activeFocus || control.hovered ? Colors.primary : Colors.outline
        StyledText {
            anchors.centerIn: parent
            text: "✓"
            visible: control.checked
            color: Colors.overPrimary
            font.pixelSize: 16
        }
    }
    contentItem: StyledText {
        id: label
        text: control.text
        color: Colors.overSurface
        wrapMode: Text.WordWrap
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        color: "transparent"
        radius: Math.min(8, Config.roundness)
        border.width: control.activeFocus ? 3 : 0
        border.color: Colors.primary
    }
}
