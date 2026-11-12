pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.modules.components
import qs.modules.theme

StyledRect {
    id: root
    property string title: ""
    property string summary: ""
    property string description: ""
    property bool expanded: false
    property bool actionsEnabled: true
    default property alias content: body.data
    Layout.fillWidth: true
    implicitHeight: column.implicitHeight + 24
    variant: "common"
    radius: Styling.radius(-2)
    border.width: 1
    border.color: Qt.alpha(Colors.outline, 0.3)
    ColumnLayout {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: Styling.spacing(10)
        SettingsButton {
            objectName: root.objectName + "-toggle"
            Layout.fillWidth: true
            text: (root.expanded ? "▾  " : "▸  ") + root.title
            font.bold: true
            onClicked: root.expanded = !root.expanded
        }
        StyledText {
            Layout.fillWidth: true
            visible: !root.expanded && root.summary !== ""
            text: root.summary
            color: Colors.overSurfaceVariant
            wrapMode: Text.Wrap
        }
        StyledText {
            Layout.fillWidth: true
            visible: root.expanded && root.description !== ""
            text: root.description
            color: Colors.overSurfaceVariant
            wrapMode: Text.Wrap
        }
        ColumnLayout { id: body; Layout.fillWidth: true; visible: root.expanded; enabled: root.actionsEnabled; spacing: Styling.spacing(12) }
    }
}
