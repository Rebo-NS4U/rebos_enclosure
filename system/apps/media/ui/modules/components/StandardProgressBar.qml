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
    // Layered translucent rails give a soft bloom without a blur pass.
    Rectangle {
        width: progressFill.width
        height: 8
        y: (parent.height - height) / 2
        radius: height / 2
        color: Qt.alpha(root.activeColor, 0.07)
        visible: width > 0
    }
    Rectangle {
        width: progressFill.width
        height: 4
        y: (parent.height - height) / 2
        radius: height / 2
        color: Qt.alpha(root.activeColor, 0.18)
        visible: width > 0
    }
    Rectangle {
        id: progressFill
        objectName: root.fillObjectName
        width: parent.width * root.normalizedValue
        height: parent.height
        radius: parent.radius
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Qt.alpha(root.activeColor, 0.38) }
            GradientStop { position: 0.6; color: root.activeColor }
            GradientStop { position: 1; color: root.foregroundColor }
        }
    }
    Rectangle {
        // A short, bright streak marks the advancing edge, not a syllable.
        width: Math.min(18, progressFill.width)
        height: parent.height
        x: progressFill.width - width
        radius: parent.radius
        visible: width > 0
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 1; color: Qt.alpha(root.foregroundColor, 0.95) }
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
