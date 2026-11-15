pragma ComponentBehavior: Bound
import QtQuick
import Quickshell.Io
import qs.modules.services
import qs.modules.theme
import qs.modules.bar
import "../services/Lyrics.js" as Lyrics

Item {
    id: root
    property real islandLeft: width / 2
    property real islandRight: width / 2
    property real stripHeight: 36
    property bool available: true
    readonly property real gap: 12
    readonly property real sideWidth: Math.max(0, Math.min(islandLeft - gap * 2,
        width - islandRight - gap * 2))
    readonly property bool estimatedTiming: LyricsService.hasText && !LyricsService.lines.length && MprisController.length > 0
    readonly property var displayLines: estimatedTiming
        ? Lyrics.estimatedLines(LyricsService.plain, MprisController.length) : LyricsService.displayLines
    LyricsClock {
        id: estimatedClock
        lines: root.estimatedTiming ? root.displayLines : []
        position: MprisController.position
        playing: MprisController.isPlaying
        rate: LyricsService.player?.rate ?? 1
        enabled: root.estimatedTiming && root.visible
        trackKey: LyricsService.trackKey
    }
    readonly property int lineIndex: Math.max(0, estimatedTiming ? estimatedClock.activeIndex : LyricsService.currentLine)
    readonly property string currentText: !LyricsService.hasText ? "" : displayLines.length
        ? (displayLines[lineIndex]?.text || "")
        : LyricsService.plain.split("\n").find(line => line.trim()) || ""
    readonly property string nextText: LyricsService.hasText
        ? displayLines[lineIndex + 1]?.text || "" : ""
    visible: available && LyricsService.stripEnabled && MprisController.trackTitle !== "" && sideWidth >= 120
    property var levels: Array(32).fill(0)
    property real visualizerMix: 1
    property bool modeReady: false
    readonly property bool showVisualizer: !LyricsService.hasText
    function updateMode() {
        modeTransition.stop();
        const destination = showVisualizer ? 1 : 0;
        if (modeReady && Motion.enabled && visible) {
            modeTransition.to = destination;
            modeTransition.restart();
        } else visualizerMix = destination;
    }
    onShowVisualizerChanged: updateMode()
    NumberAnimation {
        id: modeTransition
        target: root
        property: "visualizerMix"
        duration: Motion.enter * 1.5
        easing.type: Easing.InOutCubic
    }
    Connections {
        target: Motion
        function onEnabledChanged() { if (!Motion.enabled) root.updateMode(); }
    }
    readonly property bool captureAudio: visible && !LyricsService.hasText
        && MprisController.isPlaying && Motion.enabled
    Process {
        id: spectrumProcess
        command: ["python3", "-u", Qt.resolvedUrl("../../scripts/music_visualizer.py").toString().replace("file://", "")]
        running: root.captureAudio
        stdout: SplitParser {
            onRead: data => {
                try {
                    const values = JSON.parse(data);
                    if (Array.isArray(values) && values.length === 32
                        && values.every(value => typeof value === "number" && isFinite(value)))
                        root.levels = values.map(value => Math.max(0, Math.min(1, value)));
                } catch (_) {}
            }
        }
        onExited: root.levels = Array(32).fill(0)
    }
    // Keep lookup active even before lyrics arrive. This surface is decorative:
    // it is outside the panel input mask, so clicks pass to the app beneath it.
    Component.onCompleted: { LyricsService.viewers++; modeReady = true; updateMode(); }
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
        visible: lyric.trim() !== "" || root.visualizerMix > 0
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
            if (!lyric || lyric === displayedText) return;
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
        Item {
            id: visualizer
            objectName: "bar-lyrics-visualizer"
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            opacity: root.visualizerMix
            visible: opacity > 0
            transform: Translate { y: (1 - root.visualizerMix) * 6 }
            scale: 0.96 + root.visualizerMix * 0.04
            property real activity: MprisController.isPlaying && Motion.enabled ? 1 : 0
            Behavior on activity {
                enabled: Motion.enabled
                NumberAnimation { duration: Motion.enter; easing.type: Motion.enterCurve }
            }
            Repeater {
                model: 32
                delegate: Rectangle {
                    required property int index
                    readonly property real level: root.levels[lineSurface.upcoming ? 31 - index : index] || 0
                    x: index * (visualizer.width / 32)
                    width: Math.max(1, visualizer.width / 32 - 3)
                    height: 2 + Math.max(0, visualizer.height - 12) * level * visualizer.activity
                    y: (visualizer.height - height) / 2
                    radius: Math.min(width / 2, 3)
                    color: BarAppearance.activeColor
                    opacity: 0.35 + level * 0.6 * visualizer.activity
                    Behavior on height {
                        enabled: Motion.enabled
                        NumberAnimation { duration: Motion.feedback; easing.type: Easing.OutCubic }
                    }
                }
            }
        }
        Label {
            upcoming: lineSurface.upcoming
            objectName: "bar-lyrics-previous-text"
            text: lineSurface.previousText
            opacity: (1 - lineSurface.progress) * (1 - root.visualizerMix)
            visible: opacity > 0
            transform: Translate { y: -4 * lineSurface.progress }
        }
        Label {
            upcoming: lineSurface.upcoming
            objectName: "bar-lyrics-text"
            text: lineSurface.displayedText
            opacity: lineSurface.progress * (1 - root.visualizerMix)
            transform: Translate { y: 4 * (1 - lineSurface.progress) }
        }
    }
    Line { objectName: "bar-lyrics-current"; x: root.gap; lyric: (root.estimatedTiming && root.currentText ? "≈ " : "") + root.currentText }
    Line { objectName: "bar-lyrics-next"; x: root.width - root.sideWidth - root.gap; lyric: (root.estimatedTiming && root.nextText ? "≈ " : "") + root.nextText; upcoming: true }
}
