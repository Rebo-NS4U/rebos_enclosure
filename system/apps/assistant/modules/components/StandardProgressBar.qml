import QtQuick
import qs.modules.theme

// Shared progress rail. Values are normalized; callers own interaction.
Rectangle {
    id: root
    property real value: 0
    property bool slider: false
    property bool pressed: false
    readonly property real normalizedValue: Math.max(0, Math.min(1, isFinite(value) ? value : 0))
    property color activeColor: Colors.primary
    property color foregroundColor: Colors.overSurface
    property string fillObjectName: "standard-progress-fill"
    implicitWidth: 100
    implicitHeight: slider ? 4 + 3 * engagement : 2
    property real engagement: slider && (pressed || pulseStrength > 0) ? 1 : 0
    Behavior on engagement {
        enabled: Motion.enabled
        NumberAnimation {
            duration: root.pressed ? Motion.feedback : Motion.enter
            easing.type: Motion.feedbackCurve
        }
    }
    radius: height / 2
    color: Qt.alpha(activeColor, 0.10)
    readonly property real pulseStrength: Motion.enabled && settleTimer.running ? 1 : 0
    onNormalizedValueChanged: {
        if (Motion.enabled && visible) settleTimer.restart();
    }

    Timer {
        id: settleTimer
        interval: root.slider ? Motion.enter : 420
    }

    Rectangle {
        id: progressFill
        objectName: root.fillObjectName
        width: parent.width * root.normalizedValue
        height: parent.height
        radius: parent.radius
        color: root.activeColor
        readonly property var marks: [
            { offset: 0, width: 2, height: 2, lift: 2 },
            { offset: 5, width: 5, height: 3, lift: -1 },
            { offset: 14, width: 8, height: 2, lift: 3 }
        ]
        readonly property real markScale: Math.min(1, width / 30)
        readonly property real sweep: (1 - Math.cos(travelPhase)) / 2
        readonly property real clusterStart: width - 28 * markScale
            - Math.min(28, Math.max(0, width - 28 * markScale)) * sweep
        property real travelPhase: 0
        NumberAnimation on travelPhase {
            from: 0
            to: 2 * Math.PI
            duration: 760
            loops: Animation.Infinite
            running: root.visible && Motion.enabled && progressFill.width > 0 && progressFill.markOpacity > 0
        }

        property real markOpacity: root.slider ? 0 : root.pulseStrength
        Behavior on markOpacity {
            NumberAnimation { duration: Motion.feedback; easing.type: Easing.InOutQuad }
        }

        Repeater {
            model: progressFill.marks
            delegate: Rectangle {
                required property var modelData
                objectName: "standard-progress-mark"
                x: progressFill.clusterStart + modelData.offset * progressFill.markScale
                y: (progressFill.height - height) / 2
                    - modelData.lift * (0.5 + 0.5 * progressFill.sweep)
                width: modelData.width * progressFill.markScale
                height: modelData.height
                radius: Math.min(width, height) / 2
                color: root.foregroundColor
                opacity: progressFill.markOpacity
                visible: width > 0 && opacity > 0
            }
        }

        Rectangle {
            objectName: "slider-highlight"
            anchors.right: parent.right
            width: Math.min(parent.width, 12 + 28 * root.engagement)
            height: parent.height
            radius: parent.radius
            visible: root.slider && opacity > 0 && width > 0
            opacity: 0.42 * root.engagement
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: Qt.alpha(root.foregroundColor, 0) }
                GradientStop { position: 1; color: root.foregroundColor }
            }
        }

        Rectangle {
            objectName: "standard-progress-tip"
            visible: !root.slider
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
            y: root.slider ? (root.height - height) / 2 : -1
            width: 1
            height: 4
            radius: 0.5
            color: Qt.alpha(root.foregroundColor,
                root.normalizedValue >= (index + 1) / 4 ? 0.5 : 0.12)
        }
    }
}
