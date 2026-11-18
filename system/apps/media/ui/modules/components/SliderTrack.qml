pragma ComponentBehavior: Bound
import QtQuick
import qs.modules.theme

Item {
    id: root

    property real value: 0
    property color activeColor: Colors.primary
    property bool pressed: false
    property bool hovered: false
    property bool focused: false

    implicitHeight: 22
    readonly property real filledLength: width * Math.max(0, Math.min(1, isFinite(value) ? value : 0))
    readonly property int segmentCount: Math.max(1, Math.min(64, Math.round(width / 8)))
    readonly property real pitch: width / segmentCount
    property real energy: Motion.enabled && visible
        ? (pressed ? 1 : activity.running ? 0.65 : 0) : 0
    property real phase: 0

    readonly property real handleOffset: waveOffset(waveAt(filledLength))

    function waveAt(position: real): real {
        const distance = Math.abs(position - filledLength);
        return Math.sin(phase - 2 * Math.PI * distance / Math.max(1, width));
    }

    function waveOffset(wave: real): real {
        return -5 * energy * wave;
    }

    onHoveredChanged: if (hovered && Motion.enabled) activity.restart()
    onValueChanged: if (Motion.enabled && visible && !pressed && (hovered || focused)) activity.restart()

    Timer {
        id: activity
        interval: Motion.base * 2
    }

    Behavior on energy {
        enabled: Motion.enabled && root.visible
        NumberAnimation {
            duration: root.pressed ? Motion.enter : Motion.base * 2
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
            y: (root.height - height) / 2 + root.waveOffset(wave)
            width: Math.max(0, root.pitch - Math.min(3, root.pitch / 3))
            height: 6 + root.energy * (2.5 + 2 * wave)
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
