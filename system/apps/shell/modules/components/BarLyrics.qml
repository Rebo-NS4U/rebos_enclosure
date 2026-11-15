pragma ComponentBehavior: Bound
import QtQuick
import qs.modules.services
import qs.modules.theme
import qs.modules.bar

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

    component Label: StyledText {
        property bool upcoming: false
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        color: upcoming ? BarAppearance.mutedColor : BarAppearance.foregroundColor
        font.pixelSize: Styling.fontSize(-1)
        font.bold: false
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        maximumLineCount: 1
        elide: Text.ElideRight
    }

    component Line: StyledRect {
        id: lineSurface
        property string lyric: ""
        property bool upcoming: false
        width: root.sideWidth
        height: root.stripHeight
        visible: lyric.trim() !== ""
        variant: "bg"
        backgroundOpacity: BarAppearance.panelOpacity(false)
        topLeftRadius: BarAppearance.framed ? Styling.radius(4) : 0
        topRightRadius: topLeftRadius
        bottomLeftRadius: BarAppearance.themedCorners ? Styling.radius(4) : height / 2
        bottomRightRadius: bottomLeftRadius
        border.width: BarAppearance.framed || Styling.shellStyle === "dithered" ? 1 : 0
        border.color: BarAppearance.panelBorder(false)

        property string displayedText: ""
        property string previousText: ""
        property real progress: 1
        property bool ready: false
        readonly property bool transitioning: lyricTransition.running
        function updateText() {
            if (lyric === displayedText) return;
            // Keep the dominant label when a seek interrupts a transition.
            if (progress >= 0.5) previousText = displayedText;
            displayedText = lyric;
            lyricTransition.stop();
            if (ready && Motion.enabled && lineSurface.visible && previousText) {
                progress = 0;
                lyricTransition.start();
            } else progress = 1;
        }
        onLyricChanged: updateText()
        Component.onCompleted: { updateText(); ready = true; }
        Connections {
            target: Motion
            function onEnabledChanged() {
                if (!Motion.enabled) { lyricTransition.stop(); lineSurface.progress = 1; }
            }
        }
        NumberAnimation {
            id: lyricTransition
            target: lineSurface
            property: "progress"
            to: 1
            duration: Motion.enter
            easing.type: Motion.enterCurve
        }
        Label {
            upcoming: lineSurface.upcoming
            objectName: "bar-lyrics-previous-text"
            text: lineSurface.previousText
            opacity: 1 - lineSurface.progress
            visible: opacity > 0
            transform: Translate { y: -4 * lineSurface.progress }
        }
        Label {
            upcoming: lineSurface.upcoming
            objectName: "bar-lyrics-text"
            text: lineSurface.displayedText
            opacity: lineSurface.progress
            transform: Translate { y: 4 * (1 - lineSurface.progress) }
        }
    }
    Line { objectName: "bar-lyrics-current"; x: root.gap; lyric: root.currentText }
    Line { objectName: "bar-lyrics-next"; x: root.width - root.sideWidth - root.gap; lyric: root.nextText; upcoming: true }
}
