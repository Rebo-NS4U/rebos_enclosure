import QtQuick
import QtQuick.Controls
import qs.modules.theme

Slider {
    id: control
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    implicitHeight: 36
    implicitWidth: 160
    leftPadding: 10
    rightPadding: 10
    opacity: enabled ? 1 : 0.45
    background: StandardProgressBar {
        x: control.leftPadding
        y: control.topPadding + (control.availableHeight - height) / 2
        width: control.availableWidth
        height: 2
        value: control.position
        rotation: control.mirrored ? 180 : 0
    }
    handle: Rectangle {
        objectName: "media-slider-handle"
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: (control.height - height) / 2
        width: 18; height: 18; radius: 9
        color: control.pressed ? Colors.overSurface : Colors.primary
        border.width: control.activeFocus ? 2 : 0
        border.color: Colors.overSurface
    }
}
