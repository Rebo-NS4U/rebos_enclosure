pragma ComponentBehavior: Bound
import QtQuick
import qs.modules.theme

Item {
    id: root

    readonly property bool nebula: Styling.shellStyle === "nebula"
    property real value: 0
    property color activeColor: Colors.primary
    property bool pressed: false
    property bool playing: false
    property bool hovered: false
    property real thickness: 6
    property real rippleAmplitude: 1.5

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
        // Anchor the wave to the rail so moving the thumb only changes the taper.
        return taper * Math.sin(phase + 2 * Math.PI * position / rippleWavelength);
    }

    Behavior on energy {
        enabled: Motion.enabled && root.visible
        NumberAnimation {
            duration: Motion.base
            easing.type: Easing.InOutSine
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
            y: (root.height - height) / 2 - root.rippleAmplitude * root.energy * wave
            width: Math.max(0, root.pitch - Math.min(3, root.pitch / 3))
            height: root.nebula ? Math.min(width, root.thickness) : root.thickness
            radius: Math.min(width, height) / 2
            color: Qt.alpha(root.nebula ? Colors.overBackground : root.activeColor, root.hovered || root.pressed ? 0.35 : 0.22)

            Rectangle {
                width: Math.max(0, Math.min(segment.width, root.filledLength - segment.x))
                height: segment.height
                radius: Math.min(width, height) / 2
                color: root.nebula
                    ? (root.pressed && root.filledLength - segment.x <= root.pitch ? "#f04b39" : Colors.overBackground)
                    : root.activeColor
            }
        }
    }
}
