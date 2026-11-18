pragma ComponentBehavior: Bound
import QtQuick
import qs.modules.theme

Item {
    id: root

    property real value: 0
    property color activeColor: Colors.primary
    property bool pressed: false
    property bool playing: false
    property bool hovered: false

    implicitHeight: 22
    readonly property real filledLength: width * Math.max(0, Math.min(1, isFinite(value) ? value : 0))
    readonly property int segmentCount: Math.max(1, Math.min(64, Math.round(width / 8)))
    readonly property real pitch: width / segmentCount
    readonly property real rippleWavelength: 64
    property real energy: Motion.enabled && visible && enabled
        ? (pressed ? 1 : playing ? 0.65 : 0) : 0
    property real phase: 0

    function waveAt(position: real): real {
        const distance = filledLength - position;
        if (distance <= 0)
            return 0;
        // Keep the segments nearest the thumb on the centerline.
        const taper = Math.max(0, Math.min(1, (distance - pitch * 0.75) / Math.max(1, pitch)));
        return taper * Math.sin(phase - 2 * Math.PI * distance / rippleWavelength);
    }

    Behavior on energy {
        enabled: Motion.enabled && root.visible
        NumberAnimation {
            duration: Motion.feedback
            easing.type: Motion.feedbackCurve
        }
    }

    NumberAnimation on phase {
        from: 0
        to: 2 * Math.PI
        duration: Math.max(400, Motion.base * 6)
        loops: Animation.Infinite
        running: Motion.enabled && root.visible && root.energy > 0
    }

    Repeater {
        model: root.segmentCount
        delegate: Rectangle {
            id: segment
            required property int index
            readonly property real wave: root.waveAt(x + width / 2)
            x: index * root.pitch
            y: (root.height - height) / 2 - 1.5 * root.energy * wave
            width: Math.max(0, root.pitch - Math.min(3, root.pitch / 3))
            height: 6
            radius: Math.min(width, height) / 2
            color: Qt.alpha(root.activeColor, root.hovered || root.pressed ? 0.35 : 0.22)

            Rectangle {
                width: Math.max(0, Math.min(segment.width, root.filledLength - segment.x))
                height: segment.height
                radius: Math.min(width, height) / 2
                color: root.activeColor
            }
        }
    }
}
