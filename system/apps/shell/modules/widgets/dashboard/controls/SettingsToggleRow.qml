pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.modules.components
import qs.modules.theme

RowLayout {
    id: root
    property string label: ""
    property string description: ""
    property bool checked: false
    signal toggled(bool checked)
    Layout.fillWidth: true
    Layout.minimumHeight: 48
    spacing: 16
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 4
        StyledText { text: root.label; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        StyledText {
            visible: root.description.length > 0
            text: root.description
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Colors.overSurfaceVariant
            font.pixelSize: Styling.fontSize(-1)
        }
    }
    StyledSwitch {
        objectName: "settings-toggle-control"
        Accessible.name: root.label
        checked: root.checked
        onToggled: root.toggled(checked)
    }
}
