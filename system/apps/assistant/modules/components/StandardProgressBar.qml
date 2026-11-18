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
                // The crests follow the fill in either direction as its edge moves.
                readonly property real phase: (x - progressFill.width) * (2 * Math.PI / 20)
                height: progressFill.height + progressFill.pulseHeight * (0.5 + 0.5 * Math.cos(phase))
                radius: width / 2
                color: root.activeColor
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
