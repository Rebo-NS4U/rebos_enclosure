import QtQuick
import qs.modules.components
import qs.modules.theme

ThemeButton {
    id: root
    objectName: "island-menu-back"
    implicitWidth: Math.max(36, Styling.spacing(36))
    implicitHeight: Math.max(36, Styling.spacing(36))
    padding: Styling.spacing(8)
    text: Icons.arrowLeft
    font.family: Icons.font
    font.pixelSize: Styling.fontSize(2)
    Accessible.name: "Back to dashboard"
    StyledToolTip {
        show: root.hovered
        tooltipText: "Back to dashboard"
    }
}
