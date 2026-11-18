import QtQuick
import qs.modules.theme

// A non-interactive progress display using the slider rail.
Item {
    id: root

    property real value: 0
    property color activeColor: Colors.primary
    property bool playing: false
    property bool pressed: false
    property bool smoothValue: true
    readonly property real normalizedValue: Math.max(0, Math.min(1, isFinite(value) ? value : 0))
    property real displayedValue: normalizedValue
    readonly property alias filledLength: track.filledLength
    implicitWidth: 100
    implicitHeight: track.thickness

    Behavior on displayedValue {
        enabled: Motion.enabled && root.visible && root.smoothValue && !root.pressed
        NumberAnimation { duration: Motion.enter; easing.type: Easing.InOutSine }
    }

    onNormalizedValueChanged: {
        if (Motion.enabled && visible && smoothValue && !pressed && !playing)
            activity.restart();
    }

    Timer {
        id: activity
        interval: Motion.base * 2
    }

    SliderTrack {
        id: track
        anchors.fill: parent
        value: root.displayedValue
        activeColor: root.activeColor
        pressed: root.pressed
        playing: root.displayedValue > 0 && (root.playing || activity.running)
    }
}
