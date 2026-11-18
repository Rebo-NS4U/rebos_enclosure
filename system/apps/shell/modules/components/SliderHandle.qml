import QtQuick
import qs.modules.theme
Rectangle {
    id: root
    property bool pressed: false
    property bool focused: false
    implicitWidth: 12
    implicitHeight: 12
    radius: width / 2
    scale: pressed ? 0.92 : 1
    Behavior on scale {
        enabled: Motion.enabled
        NumberAnimation {
            duration: root.pressed ? Motion.press : Motion.enter
            easing.type: Motion.feedbackCurve
        }
    }
    color: Colors.primary
    border.width: focused ? 2 : 0
    border.color: Colors.overSurface
}
