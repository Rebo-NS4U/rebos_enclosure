import QtQuick
import qs.modules.components
import qs.modules.theme

ThemeButton {
    id: root
    required property string description
    implicitWidth: Styling.spacing(36)
    implicitHeight: implicitWidth
    padding: 0
    Accessible.name: description
    StyledToolTip { show: root.hovered; tooltipText: root.description }
}
