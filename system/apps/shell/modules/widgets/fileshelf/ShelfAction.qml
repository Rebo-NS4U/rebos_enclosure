pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import qs.modules.components
import qs.modules.theme

ToolButton {
    id: root
    required property string glyph
    required property string description
    implicitWidth: Styling.fontSize(0) * 2.4
    implicitHeight: implicitWidth
    focusPolicy: Qt.StrongFocus
    opacity: enabled ? 1 : 0.45
    Accessible.name: description
    background: StyledRect {
        variant: root.hovered || root.down ? "focus" : "common"
        radius: Styling.radius(-4)
        border.width: root.activeFocus ? 2 : 1
        border.color: Colors.primary
        opacity: root.enabled ? 1 : 0.4
    }
    contentItem: StyledText {
        text: root.glyph
        font.family: Icons.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        color: root.enabled ? Colors.overSurface : Colors.overSurfaceVariant
    }
    StyledToolTip { show: root.hovered; description: root.description }
}
