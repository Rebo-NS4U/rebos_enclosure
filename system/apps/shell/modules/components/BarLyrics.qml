pragma ComponentBehavior: Bound
import QtQuick
import qs.modules.services
import qs.modules.theme

Item {
    id: root
    property real islandLeft: width / 2
    property real islandRight: width / 2
    property real stripHeight: 36
    property bool available: true
    readonly property real gap: 12
    readonly property real sideWidth: Math.max(0, Math.min(islandLeft - gap * 2,
        width - islandRight - gap * 2))
    readonly property int lineIndex: Math.max(0, LyricsService.currentLine)
    readonly property string currentText: !LyricsService.hasText ? (LyricsService.status || MprisController.trackTitle) : LyricsService.lines.length
        ? (LyricsService.displayLines[lineIndex]?.text || "")
        : LyricsService.plain.split("\n").find(line => line.trim()) || ""
    readonly property string nextText: LyricsService.hasText
        ? LyricsService.displayLines[lineIndex + 1]?.text || "" : MprisController.trackArtists
    visible: available && LyricsService.stripEnabled && MprisController.trackTitle !== "" && sideWidth >= 120
    // Keep lookup active even before lyrics arrive. This surface is decorative:
    // it is outside the panel input mask, so clicks pass to the app beneath it.
    Component.onCompleted: LyricsService.viewers++
    Component.onDestruction: LyricsService.viewers = Math.max(0, LyricsService.viewers - 1)

    component Line: StyledRect {
        id: lineSurface
        property string lyric: ""
        property bool upcoming: false
        width: root.sideWidth
        height: root.stripHeight
        visible: lyric.trim() !== ""
        variant: "common"
        radius: Styling.radius(4)
        StyledText {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            objectName: "bar-lyrics-text"
            text: lineSurface.lyric
            color: lineSurface.upcoming ? Colors.overSurfaceVariant : Colors.primary
            font.bold: !lineSurface.upcoming
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            maximumLineCount: 1
            elide: Text.ElideRight
        }
    }
    Line { objectName: "bar-lyrics-current"; x: root.gap; lyric: root.currentText }
    Line { objectName: "bar-lyrics-next"; x: root.width - root.sideWidth - root.gap; lyric: root.nextText; upcoming: true }
}
