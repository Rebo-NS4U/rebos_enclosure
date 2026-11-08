import QtQuick
import QtQuick.Controls
import qs.config
import qs.modules.theme

Button {
    id: root
    focusPolicy: Qt.StrongFocus
    Accessible.name: text
    hoverEnabled: true
    implicitHeight: Math.max(36, implicitContentHeight + padding * 2)
    padding: 10
    font.family: Config.theme.font
    font.pixelSize: Styling.fontSize(-1)
    opacity: enabled ? 1 : 0.45
    background: StyledRect {
        variant: root.highlighted || root.checked ? "primary" : (root.hovered || root.down ? "focus" : "common")
        radius: Styling.radius(-4)
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus ? Colors.primary : Qt.alpha(Colors.outline, 0.3)
    }
    contentItem: StyledText {
        text: root.text
        color: root.highlighted || root.checked ? Colors.overPrimary : Colors.overSurface
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        font: root.font
    }
}
