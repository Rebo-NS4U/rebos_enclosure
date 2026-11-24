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
    property bool showCursor: true
    readonly property real normalizedValue: Math.max(0, Math.min(1, isFinite(value) ? value : 0))
    property real displayedValue: normalizedValue
    readonly property alias filledLength: track.filledLength
    implicitWidth: 100
    implicitHeight: track.thickness

    Behavior on displayedValue {
        enabled: Motion.enabled && root.visible && root.smoothValue && !root.pressed
        NumberAnimation { duration: Motion.enter; easing.type: Easing.InOutSine }
    }

    SliderTrack {
        id: track
        anchors.fill: parent
        value: root.displayedValue
        activeColor: root.activeColor
        pressed: root.pressed
        playing: root.displayedValue > 0 && root.playing
    }

    Rectangle {
        objectName: "progress-cursor"
        visible: root.showCursor && root.width > 0
        anchors.verticalCenter: parent.verticalCenter
        x: Math.max(0, Math.min(root.width - width, track.filledLength - width / 2))
        width: Math.min(4, root.width)
        height: track.thickness + 4
        radius: width / 2
        color: "white"
        border.width: 3
        border.color: Colors.surface
    }
}
