import QtQuick
import qs.modules.theme

Item {
    id: root

    property bool pressed: false
    property bool hovered: false
    property bool focused: false
    property bool vertical: false
    property real radius: width / 2
    property color accent: Colors.primary
    readonly property real railThickness: 3 + engagement
    property real engagement: pressed ? 2 : hovered ? 1 : 0

    implicitWidth: 12
    implicitHeight: 12

    Behavior on engagement {
        enabled: Motion.enabled
        NumberAnimation {
            duration: root.pressed ? Motion.feedback : Motion.enter
            easing.type: Motion.feedbackCurve
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 18 + root.engagement * 4
        height: width
        radius: width / 2
        color: root.accent
        opacity: root.engagement * 0.11
        visible: opacity > 0
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.accent
        border.width: root.focused ? 2 : 0
        border.color: Colors.overSurface
        transform: Scale {
            origin.x: root.width / 2
            origin.y: root.height / 2
            xScale: root.vertical ? 1 + 0.16 * grip : 1 - 0.20 * grip
            yScale: root.vertical ? 1 - 0.20 * grip : 1 + 0.16 * grip
            property real grip: root.pressed ? 1 : 0

            Behavior on grip {
                enabled: Motion.enabled
                NumberAnimation {
                    duration: root.pressed ? Motion.feedback : Motion.base
                    easing.type: root.pressed ? Motion.feedbackCurve : Easing.OutBack
                    easing.overshoot: 0.8
                }
            }
        }
    }
}
