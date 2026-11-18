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
    background: Item {
        x: control.leftPadding
        y: control.topPadding
        width: control.availableWidth
        height: control.availableHeight

        SliderTrack {
            anchors.centerIn: parent
            width: Math.max(0, parent.width - control.handle.width)
            value: control.position
            rotation: control.mirrored ? 180 : 0
            hovered: control.hovered
            pressed: control.pressed
        }
    }
    handle: Rectangle {
        objectName: "media-slider-handle"
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + (control.availableHeight - height) / 2
        width: 18; height: 18; radius: 9
        color: control.pressed ? Colors.overSurface : Colors.primary
        border.width: control.activeFocus ? 2 : 0
        border.color: Colors.overSurface
    }
}
