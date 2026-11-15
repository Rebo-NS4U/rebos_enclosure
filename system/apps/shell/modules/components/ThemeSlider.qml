import QtQuick
import QtQuick.Controls
import qs.modules.theme
Slider {
    id: root
    implicitHeight: 32
    implicitWidth: 100
    padding: 8
    focusPolicy: Qt.StrongFocus
    wheelEnabled: false
    opacity: enabled ? 1 : 0.45
    background: StandardProgressBar {
        x: root.leftPadding
        y: root.topPadding + (root.availableHeight - height) / 2
        width: root.availableWidth
        height: 2
        value: root.position
        rotation: root.mirrored ? 180 : 0
    }
    handle: SliderHandle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + (root.availableHeight - height) / 2
        focused: root.activeFocus
    }
}
