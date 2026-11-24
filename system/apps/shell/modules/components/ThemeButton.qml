import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.config
import qs.modules.theme

Button {
    id: root
    readonly property bool hardware: Styling.shellStyle === "terminal-hardware"
    readonly property bool glyphStyle: Styling.shellStyle === "glyph"
    readonly property bool orbital: Styling.shellStyle === "orbital"
    property string glyph: ""
    property int glyphSize: Styling.fontSize(2)
    property bool glyphSpinning: false
    property bool danger: false
    property bool emphasized: false
    readonly property bool engaged: highlighted || checked || emphasized

    focusPolicy: Qt.StrongFocus
    Accessible.name: text
    hoverEnabled: true
    implicitHeight: Math.max(Styling.spacing(36), implicitContentHeight + padding * 2)
    padding: Styling.spacing(10)
    font.family: Config.theme.font
    font.pixelSize: Styling.fontSize(-1)
    opacity: enabled ? 1 : 0.45
    background: StyledRect {
        buttonSurface: true
        controlPressed: root.down
        variant: root.danger && (root.engaged || root.hovered || root.down || root.activeFocus) ? "error"
            : root.engaged ? (root.hovered || root.down ? "primaryfocus" : "primary")
            : (root.hardware || root.orbital) && root.down ? "internalbg"
            : root.hovered || root.down ? "focus" : "common"
        radius: Styling.radius(0)
        border.pixelAligned: !root.orbital
        border.width: Config.controlBorderWidth
        border.color: root.orbital && !root.visualFocus
            ? (root.engaged || root.danger && (root.hovered || root.down) ? Qt.alpha(itemColor, root.down ? 0.7 : root.hovered ? 0.48 : 0.24)
                : root.down || root.hovered ? Qt.alpha(Colors.primary, root.down ? 0.82 : 0.62)
                : Qt.alpha(Colors.outline, 0.36))
            : root.activeFocus ? (root.danger || root.engaged ? itemColor : Colors.primary)
            : root.hardware || root.glyphStyle ? Config.resolveColor(borderData?.[0] ?? "transparent")
            : Qt.alpha(Colors.outline, 0.3)
    }
    contentItem: RowLayout {
        spacing: Styling.spacing(6)

        StyledText {
            visible: root.glyph !== ""
            Layout.alignment: Qt.AlignHCenter
            text: root.glyph
            textFormat: Text.RichText
            font.family: Icons.font
            font.pixelSize: root.glyphSize
            color: root.danger && root.background.variant !== "error" ? Colors.error : root.background.itemColor

            RotationAnimation on rotation {
                running: root.glyphSpinning && Config.animDuration > 0
                from: 0
                to: 360
                duration: 1000
                loops: Animation.Infinite
            }
        }

        StyledText {
            visible: root.text !== ""
            Layout.fillWidth: true
            text: root.text
            color: root.background.itemColor
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            font: root.font
        }
    }
}
