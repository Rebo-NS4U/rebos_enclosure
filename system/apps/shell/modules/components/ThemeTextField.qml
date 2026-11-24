import QtQuick
import QtQuick.Controls
import qs.config
import qs.modules.theme

TextField {
    id: root
    implicitHeight: Math.max(Styling.spacing(48), contentHeight + padding * 2)
    padding: Styling.spacing(12)
    font.family: Config.theme.font
    font.pixelSize: Styling.fontSize(0)
    color: background.itemColor
    placeholderTextColor: Colors.overSurfaceVariant
    selectionColor: Colors.primary
    selectedTextColor: Colors.overPrimary
    selectByMouse: true
    background: StyledRect {
        variant: "internalbg"
        radius: Styling.radius(-4)
        border.width: 3
        border.color: root.activeFocus ? Colors.primary : Qt.alpha(Colors.outline, 0.3)
    }
}
