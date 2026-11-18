import QtQuick
import qs.modules.theme

// Shared progress rail. Values are normalized; callers own interaction.
Rectangle {
    id: root
    property real value: 0
    readonly property real normalizedValue: Math.max(0, Math.min(1, isFinite(value) ? value : 0))
    property color activeColor: Colors.primary
    property color foregroundColor: Colors.overSurface
    property string fillObjectName: "standard-progress-fill"
    implicitWidth: 100
    implicitHeight: 2
    radius: height / 2
    color: Qt.alpha(activeColor, 0.10)
    readonly property real pulseStrength: Motion.enabled && settleTimer.running ? 1 : 0
    onNormalizedValueChanged: {
        if (Motion.enabled && visible) settleTimer.restart();
    }

    Timer {
        id: settleTimer
        interval: 420
    }

    Rectangle {
        id: progressFill
        objectName: root.fillObjectName
        width: parent.width * root.normalizedValue
        height: parent.height
        radius: parent.radius
        color: root.activeColor
        readonly property int stepSpacing: 4
        property real travelPhase: 0
        NumberAnimation on travelPhase {
            from: 0
            to: 2 * Math.PI
            duration: 480
            loops: Animation.Infinite
            running: root.visible && Motion.enabled && progressFill.width > 0 && progressFill.pulseHeight > 0
        }

        property real pulseHeight: 6 * root.pulseStrength
        Behavior on pulseHeight {
            NumberAnimation { duration: Motion.feedback; easing.type: Easing.InOutQuad }
        }

        Repeater {
            model: Math.ceil(root.width / progressFill.stepSpacing)
            delegate: Rectangle {
                required property int index
                objectName: "standard-progress-step"
                x: index * progressFill.stepSpacing
                anchors.verticalCenter: parent.verticalCenter
                width: Math.max(0, Math.min(2, progressFill.width - x))
                readonly property real phase: (x - progressFill.width) * (2 * Math.PI / 24) - progressFill.travelPhase
                readonly property real crest: (1 + Math.cos(phase)) / 2
                height: progressFill.height + progressFill.pulseHeight * crest * crest
                radius: width / 2
                color: Qt.tint(root.activeColor,
                    Qt.alpha(root.foregroundColor, 0.55 * crest * crest * progressFill.pulseHeight / 6))
                visible: width > 0 && progressFill.pulseHeight > 0
            }
        }

        Rectangle {
            objectName: "standard-progress-tip"
            anchors.right: parent.right
            width: Math.min(parent.width, parent.height * 2)
            height: parent.height
            radius: parent.radius
            color: root.foregroundColor
        }
    }
    Repeater {
        model: 3
        delegate: Rectangle {
            required property int index
            x: (index + 1) * root.width / 4
            y: -1
            width: 1
            height: 4
            radius: 0.5
            color: Qt.alpha(root.foregroundColor,
                root.normalizedValue >= (index + 1) / 4 ? 0.5 : 0.12)
        }
    }
}
