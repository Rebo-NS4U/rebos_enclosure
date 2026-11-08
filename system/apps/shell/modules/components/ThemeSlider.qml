import QtQuick
import QtQuick.Controls
import qs.modules.theme
Slider {
    id: root
    implicitHeight: 32
    implicitWidth: 100
    padding: 8
    focusPolicy: Qt.StrongFocus
    wheelEnabled: true
    opacity: enabled ? 1 : 0.45
    background: Rectangle {
        x: root.leftPadding
        y: root.topPadding + (root.availableHeight - height) / 2
        width: root.availableWidth
        height: 4
        radius: 2
        color: Colors.outlineVariant
        Rectangle { width: root.visualPosition * parent.width; height: parent.height; radius: 2; color: Colors.primary }
    }
    handle: SliderHandle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + (root.availableHeight - height) / 2
        focused: root.activeFocus
    }
}
