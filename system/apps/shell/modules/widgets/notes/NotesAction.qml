import QtQuick
import qs.modules.components
import qs.modules.theme

ThemeButton {
    id: root
    required property string label
    implicitWidth: Styling.spacing(36)
    implicitHeight: implicitWidth
    padding: 0
    Accessible.name: label
    StyledToolTip { show: root.hovered; tooltipText: root.label }
}
