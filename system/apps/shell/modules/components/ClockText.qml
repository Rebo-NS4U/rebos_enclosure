import QtQuick
import qs.modules.theme

StyledText {
    id: root
    required property string clockValue
    readonly property bool glyphClock: Styling.shellStyle === "glyph"
    Accessible.name: clockValue
    textFormat: glyphClock ? Text.StyledText : Text.PlainText
    // Align the two circles with the digit ink, independent of the font's colon.
    readonly property string separator: {
        const svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 24' fill='#f2f2f2'>"
            + "<circle cx='5' cy='7' r='2.5'/><circle cx='5' cy='17' r='2.5'/></svg>";
        return "<img src='data:image/svg+xml;base64," + Qt.btoa(Array.from(svg, ch => ch.charCodeAt(0))) + "' width='"
            + Math.max(4, Math.round(font.pixelSize * 0.28)) + "' height='"
            + Math.round(font.pixelSize * 0.67) + "' align='middle'/>";
    }
    text: glyphClock ? clockValue.replace(/:/g, separator) : clockValue
}
