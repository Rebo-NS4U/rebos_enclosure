import QtQuick
import QtQuick.Controls
import qs.config
import qs.modules.theme

Button {
    id: root
    readonly property bool hardware: Styling.shellStyle === "terminal-hardware"
    focusPolicy: Qt.StrongFocus
    Accessible.name: text
    hoverEnabled: true
    implicitHeight: Math.max(Styling.spacing(36), implicitContentHeight + padding * 2)
    padding: Styling.spacing(10)
    font.family: Config.theme.font
    font.pixelSize: Styling.fontSize(-1)
    opacity: enabled ? 1 : 0.45
    background: StyledRect {
        controlSurface: root.hardware
        controlPressed: root.down
        variant: root.hardware && root.down && !root.highlighted && !root.checked ? "internalbg" : root.highlighted || root.checked ? "primary" : (root.hovered || root.down ? "focus" : "common")
        radius: Styling.radius(-4)
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus ? Colors.primary : root.hardware ? Config.resolveColor(borderData?.[0] ?? "transparent") : Qt.alpha(Colors.outline, 0.3)
    }
    contentItem: StyledText {
        text: root.text
        color: root.background.itemColor
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        font: root.font
    }
}
