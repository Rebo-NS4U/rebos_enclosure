import QtQuick
import qs.modules.theme

// Shared lyrics-style rail. Values are normalized; callers own interaction.
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
    // Two translucent bands give the filled rail a soft edge.
    Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        width: progressFill.width
        height: parent.height + 6
        radius: height / 2
        color: Qt.alpha(root.activeColor, 0.07)
    }
    Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        width: progressFill.width
        height: parent.height + 2
        radius: height / 2
        color: Qt.alpha(root.activeColor, 0.18)
    }
    Rectangle {
        id: progressFill
        objectName: root.fillObjectName
        width: parent.width * root.normalizedValue
        height: parent.height
        radius: parent.radius
        color: root.activeColor

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
