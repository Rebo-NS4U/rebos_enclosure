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
    Rectangle {
        id: progressFill
        objectName: root.fillObjectName
        width: parent.width * root.normalizedValue
        height: parent.height
        radius: parent.radius
        color: root.activeColor
        readonly property int stepSpacing: 4
        readonly property list<int> stepRise: [1, 3, 6, 4, 2]

        Repeater {
            model: Math.ceil(root.width / progressFill.stepSpacing)
            delegate: Rectangle {
                required property int index
                objectName: "standard-progress-step"
                x: index * progressFill.stepSpacing
                anchors.verticalCenter: parent.verticalCenter
                width: Math.max(0, Math.min(2, progressFill.width - x))
                height: progressFill.height + progressFill.stepRise[index % progressFill.stepRise.length]
                radius: width / 2
                color: root.activeColor
                visible: width > 0
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
