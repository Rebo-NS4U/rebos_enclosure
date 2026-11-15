pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.modules.components
import qs.modules.theme

StyledRect {
    id: root
    property string title: ""
    property string description: ""
    property bool collapsible: false
    property bool expanded: false
    default property alias content: body.data
    Layout.fillWidth: true
    implicitHeight: column.implicitHeight + 40
    variant: "common"
    radius: Styling.radius(-2)
    border.width: 1
    border.color: Qt.alpha(Colors.outline, 0.3)
    ColumnLayout {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 20
        spacing: Styling.spacing(16)
        StyledText { visible: !root.collapsible && root.title.length > 0; text: root.title; font.bold: true; font.pixelSize: Styling.fontSize(1); Layout.fillWidth: true; wrapMode: Text.WordWrap }
        SettingsButton {
            objectName: root.objectName + "-expand"
            visible: root.collapsible
            Layout.fillWidth: true
            text: (root.expanded ? "▾  " : "▸  ") + root.title
            Accessible.name: root.title
            Accessible.description: root.expanded ? "Expanded" : "Collapsed"
            onClicked: root.expanded = !root.expanded
        }
        StyledText {
            visible: (!root.collapsible || root.expanded) && root.description.length > 0
            Layout.fillWidth: true
            text: root.description
            wrapMode: Text.WordWrap
            color: Colors.overSurfaceVariant
            font.pixelSize: Styling.fontSize(-1)
        }
        ColumnLayout { id: body; visible: !root.collapsible || root.expanded; Layout.fillWidth: true; spacing: Styling.spacing(16) }
    }
}
