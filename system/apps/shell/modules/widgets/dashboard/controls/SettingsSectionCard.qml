pragma ComponentBehavior: Bound
import QtQuick
import qs.config
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.components
import qs.modules.theme

Button {
    id: root
    focusPolicy: Qt.StrongFocus
    opacity: enabled ? 1 : 0.45
    Accessible.name: text
    property string description: ""
    property string glyph: ""
    property bool selected: false
    Layout.fillWidth: true
    Layout.minimumWidth: 0
    implicitHeight: Math.max(Styling.spacing(80), contentItem.implicitHeight + padding * 2)
    padding: Styling.spacing(16)
    hoverEnabled: true
    background: StyledRect {
        variant: root.hovered || root.down ? "focus" : "common"
        radius: Styling.radius(-2)
        border.width: Config.controlBorderWidth
        border.color: root.activeFocus || root.selected ? Colors.primary : Qt.alpha(Colors.outline, 0.3)
    }
    contentItem: RowLayout {
        spacing: Styling.spacing(12)
        StyledRect {
            id: iconTile
            visible: root.glyph.length > 0
            Layout.preferredWidth: Styling.spacing(36)
            Layout.preferredHeight: Styling.spacing(36)
            variant: root.selected ? "primary" : "oversecondary"
            StyledText {
                anchors.centerIn: parent
                text: root.glyph
                color: iconTile.itemColor
                font.family: Icons.font
                font.pixelSize: Styling.fontSize(5)
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(6)
            StyledText {
                Layout.fillWidth: true
                text: root.text
                font.family: Styling.displayFont
                color: root.background.itemColor
                font.bold: true
                wrapMode: Text.WordWrap
            }
            StyledText {
                Layout.fillWidth: true
                text: root.description
                visible: text.length > 0
                wrapMode: Text.WordWrap
                color: Colors.overSurfaceVariant
                font.pixelSize: Styling.fontSize(-1)
            }
        }
        StyledText { text: Icons.caretRight; font.family: Icons.font; color: Colors.overSurfaceVariant }
    }
}
