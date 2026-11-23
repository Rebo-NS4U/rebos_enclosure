pragma ComponentBehavior: Bound
import QtQuick
import qs.config
import qs.modules.theme

// Shared text primitive. Qt's default distance-field renderer (QtRendering)
// produces a soft halo on small/bold UI glyphs; native hinted rendering keeps
// edges crisp for static shell chrome. Prefer this over bare Text for labels.
Text {
    id: root

    color: Colors.overBackground
    font.family: Config.theme.font
    font.pixelSize: Styling.fontSize(0)
    font.letterSpacing: Styling.shellStyle === "glyph" && font.pixelSize >= 18 ? 0.6 : 0
    layer.enabled: Styling.shellStyle === "glyph" && font.pixelSize >= 18 && textFormat !== Text.RichText
    layer.effect: ShaderEffect {
        property var source
        property size labelSize: Qt.size(root.width, root.height)
        fragmentShader: Qt.resolvedUrl("nebula_type.frag.qsb")
    }
    renderType: Text.NativeRendering
    font.hintingPreference: Font.PreferFullHinting
}
