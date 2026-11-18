import QtQuick
import qs.modules.theme
import qs.modules.components
import qs.config

ThemeButton {
    id: root
    property int count: 1
    property bool expanded: false
    property real fontSize: Config.theme.fontSize

    visible: count > 1
    implicitWidth: contentItem.implicitWidth + Styling.spacing(12)
    implicitHeight: Styling.spacing(26)
    padding: 0
    text: String(count)
    glyph: expanded ? Icons.caretUp : Icons.caretDown
    glyphSize: fontSize
    font.pixelSize: fontSize
    font.weight: Font.Bold
    emphasized: expanded
    Accessible.name: expanded ? "Collapse notifications" : "Expand " + count + " notifications"
}
