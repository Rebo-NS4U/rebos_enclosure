pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.modules.services
import qs.modules.theme
import qs.modules.bar
import "../services/Lyrics.js" as Lyrics

Item {
    id: root
    property bool inlineMode: false
    property bool splitAroundCenter: false
    property bool connectedMode: false
    property Item calibrationParent: root
    signal openMedia()
    property real islandLeft: width / 2
    property real islandRight: width / 2
    property real stripHeight: 36
    property bool available: true
    readonly property real gap: connectedMode ? 0 : 12
    // Match the tiled workspace edge while keeping breathing room by the island.
    readonly property real edgeMargin: inlineMode || connectedMode ? 0 : 4
    readonly property real sideWidth: inlineMode && !splitAroundCenter ? width / 2 : Math.max(0, Math.min(islandLeft - gap - edgeMargin,
        width - islandRight - gap - edgeMargin))
    readonly property Region backgroundBlur: Region {
        regions: [
            BlurRegion { target: currentPanel; enabled: root.visible },
            BlurRegion { target: nextPanel; enabled: root.visible }
        ]
    }
    readonly property bool estimatedTiming: LyricsService.hasText && !LyricsService.lines.length && MprisController.length > 0
    readonly property var displayLines: estimatedTiming
        ? Lyrics.estimatedLines(LyricsService.plain, MprisController.length) : LyricsService.displayLines
    LyricsClock {
        id: estimatedClock
        lines: root.estimatedTiming ? root.displayLines : []
        position: MprisController.position + root.estimatedTimeOffset
        playing: MprisController.isPlaying
        rate: LyricsService.player?.rate ?? 1
        enabled: root.estimatedTiming && root.visible
        trackKey: LyricsService.trackKey
    }
    property int estimatedOffset: 0
    property real estimatedTimeOffset: 0
    property bool calibrationOpen: false
    readonly property int estimatedBaseIndex: Math.max(0, estimatedClock.activeIndex)
    readonly property int lineIndex: estimatedTiming
        ? Math.max(0, Math.min(displayLines.length - 1, estimatedBaseIndex + estimatedOffset))
        : Math.max(0, LyricsService.currentLine)
    // Show elapsed time within the current line; no word or syllable timing is inferred.
    property real lyricPosition: 0
    function updateLyricPosition() {
        lyricPosition = estimatedTiming ? estimatedClock.currentTime() : LyricsService.playbackClock.currentTime();
    }
    Timer {
        interval: 16
        running: root.visible && LyricsService.hasText && MprisController.isPlaying && Motion.enabled
        repeat: true
        triggeredOnStart: true
        onTriggered: root.updateLyricPosition()
    }
    Connections {
        target: MprisController
        function onPositionChanged() { root.updateLyricPosition(); }
        function onIsPlayingChanged() { root.updateLyricPosition(); }
    }
    readonly property real lineStart: displayLines[lineIndex]?.time ?? 0
    readonly property real lineEnd: displayLines[lineIndex + 1]?.time ?? MprisController.length
    readonly property real lineProgress: Math.max(0, Math.min(1,
        (lyricPosition - lineStart) / Math.max(0.1, lineEnd - lineStart)))
    readonly property bool canStepBack: estimatedTiming && lineIndex > 0
    readonly property bool canStepForward: estimatedTiming && lineIndex < displayLines.length - 1
    readonly property Item previousHitbox: visible && estimatedTiming && currentPanel.visible ? currentPanel.control : null
    readonly property Item nextHitbox: visible && estimatedTiming && currentPanel.visible ? currentPanel.forwardControl : null
    readonly property Item calibrationButtonHitbox: visible && estimatedTiming && nextPanel.visible ? nextPanel.control : null
    readonly property Item calibrationHitbox: calibrationPanel.visible ? calibrationPanel : null
    function resetCalibration() { estimatedOffset = 0; estimatedTimeOffset = 0; calibrationOpen = false; }
    function calibrateLine(index) {
        if (!estimatedTiming || index < 0 || index >= displayLines.length || Math.floor(index) !== index) return;
        const playbackAt = MprisController.position;
        estimatedOffset = 0;
        estimatedTimeOffset = displayLines[index].time - playbackAt;
        estimatedClock.reanchor();
        calibrationOpen = false;
    }
    function stepEstimatedLine(direction) {
        if (!estimatedTiming || !displayLines.length || (direction !== -1 && direction !== 1)) return;
        const target = Math.max(0, Math.min(displayLines.length - 1, lineIndex + direction));
        estimatedOffset = target - estimatedBaseIndex;
    }
    onEstimatedTimingChanged: if (!estimatedTiming) resetCalibration()
    Connections {
        target: LyricsService
        function onTrackKeyChanged() { root.resetCalibration(); }
        function onPlainChanged() { root.resetCalibration(); }
    }
    readonly property string currentText: !LyricsService.hasText ? "" : displayLines.length
        ? (displayLines[lineIndex]?.text || "")
        : LyricsService.plain.split("\n").find(line => line.trim()) || ""
    readonly property string nextText: LyricsService.hasText
        ? displayLines[lineIndex + 1]?.text || "" : ""
    visible: available && LyricsService.stripEnabled && MprisController.trackTitle !== "" && sideWidth >= 120
    onVisibleChanged: if (!visible) calibrationOpen = false
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
    readonly property bool captureAudio: visible && MprisController.isPlaying && Motion.enabled
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
    // Inline surfaces share the bar hitbox; line controls retain their own actions.
    Component.onCompleted: { LyricsService.viewers++; modeReady = true; updateMode(); }
    Component.onDestruction: LyricsService.viewers = Math.max(0, LyricsService.viewers - 1)

    component PanelControl: ThemeButton {
        id: button
        property bool muted: false
        width: 24; height: 24; padding: 0
        anchors.verticalCenter: parent.verticalCenter
        StyledToolTip {
            show: button.hovered && button.enabled
            tooltipText: button.Accessible.name
        }
        background: Rectangle {
            radius: 8
            color: Qt.alpha(BarAppearance.activeColor, button.down ? 0.28 : button.hovered ? 0.22 : button.muted ? 0.09 : 0.16)
            border.width: button.activeFocus ? 2 : 1
            border.color: Qt.alpha(BarAppearance.activeColor, button.hovered ? 0.4 : 0.16)
        }
        contentItem: StyledText {
            text: button.text
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: Styling.fontSize(2)
            color: button.muted ? BarAppearance.mutedColor : BarAppearance.activeColor
        }
    }

    component Label: StyledText {
        property bool upcoming: false
        anchors.fill: parent
        anchors.leftMargin: upcoming ? 18 : root.estimatedTiming ? 72 : 44
        anchors.rightMargin: upcoming ? 44 : 18
        color: upcoming ? BarAppearance.mutedColor : BarAppearance.foregroundColor
        font.pixelSize: Styling.fontSize(-1)
        font.weight: upcoming ? Font.Normal : Font.Medium
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        maximumLineCount: 1
        elide: Text.ElideRight
    }

    component Line: StyledRect {
        id: lineSurface
        property string lyric: ""
        property bool upcoming: false
        readonly property alias control: modeBadge
        readonly property alias forwardControl: forwardBadge
        width: root.sideWidth
        height: root.stripHeight
        visible: lyric.trim() !== "" || root.visualizerMix > 0 || (upcoming && root.estimatedTiming)
        variant: "bg"
        backgroundOpacity: root.inlineMode ? 0 : BarAppearance.panelOpacity(root.connectedMode)
        topLeftRadius: root.connectedMode ? 0 : BarAppearance.framed ? Styling.radius(4) : 0
        topRightRadius: root.connectedMode ? 0 : topLeftRadius
        bottomLeftRadius: root.connectedMode && upcoming ? 0 : BarAppearance.themedCorners ? Styling.radius(4) : height / 2
        bottomRightRadius: root.connectedMode ? (upcoming ? (BarAppearance.themedCorners ? Styling.radius(4) : height / 2) : 0) : bottomLeftRadius
        border.width: !root.inlineMode && !root.connectedMode && BarAppearance.framed ? 1 : 0
        border.color: BarAppearance.panelBorder(false)

        MouseArea {
            anchors.fill: parent
            enabled: root.inlineMode
            cursorShape: Qt.PointingHandCursor
            onClicked: root.openMedia()
        }
        PanelControl {
            id: modeBadge
            objectName: lineSurface.upcoming ? "lyrics-calibrate" : "lyrics-step-back"
            x: lineSurface.upcoming ? lineSurface.width - width - 7 : 7
            muted: lineSurface.upcoming
            enabled: lineSurface.upcoming ? root.estimatedTiming : root.canStepBack
            opacity: (root.estimatedTiming || lineSurface.upcoming) && !enabled ? 0.35 : 1
            text: lineSurface.upcoming ? (root.estimatedTiming ? "◎" : "♪")
                : root.estimatedTiming ? "‹" : root.visualizerMix > 0.5 ? "≋" : "♪"
            Accessible.name: lineSurface.upcoming ? "Calibrate estimated lyrics" : "Previous estimated lyric line"
            onClicked: {
                if (lineSurface.upcoming) root.calibrationOpen = !root.calibrationOpen;
                else root.stepEstimatedLine(-1);
            }
        }
        PanelControl {
            id: forwardBadge
            objectName: "lyrics-step-forward"
            x: 35
            visible: !lineSurface.upcoming && root.estimatedTiming
            enabled: root.canStepForward
            text: "›"
            Accessible.name: "Next estimated lyric line"
            onClicked: root.stepEstimatedLine(1)
        }
        Rectangle {
            objectName: "bar-lyrics-playback-accent"
            x: lineSurface.upcoming ? lineSurface.width - width - 16 : 16
            y: lineSurface.height - 3
            width: Math.max(0, lineSurface.width - 32) * (MprisController.length > 0
                ? Math.min(1, Math.max(0, MprisController.position / MprisController.length)) : 0)
            height: 1
            radius: 0.5
            color: Qt.alpha(BarAppearance.activeColor, 0.5)
        }

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
            anchors.leftMargin: lineSurface.upcoming ? 16 : 44
            anchors.rightMargin: lineSurface.upcoming ? 44 : 16
            // Retain a quiet spectrum behind readable foreground lyrics.
            opacity: 0.24 + root.visualizerMix * 0.76
            visible: opacity > 0
            // Leave a generous quiet pocket around the actual text, with a
            // feathered edge so the spectrum does not end in a hard rectangle.
            readonly property real textPadding: 24
            readonly property real textHalfWidth: Math.min(currentLabel.contentWidth, currentLabel.width) / 2
            readonly property real textCenter: currentLabel.x + currentLabel.width / 2 - x
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
                    height: 2 + Math.max(0, visualizer.height - 10) * level * visualizer.activity
                    y: (visualizer.height - height) / 2
                    radius: Math.min(width / 2, 3)
                    gradient: Gradient {
                        GradientStop { position: 0; color: Qt.alpha(BarAppearance.foregroundColor, 0.82) }
                        GradientStop { position: 0.35; color: BarAppearance.activeColor }
                        GradientStop { position: 1; color: Qt.alpha(BarAppearance.activeColor, 0.42) }
                    }
                    readonly property real textDistance: Math.abs(x + width / 2 - visualizer.textCenter)
                    readonly property real quietMix: lineSurface.lyric.trim() === "" ? 0
                        : Math.max(0, Math.min(1, (visualizer.textHalfWidth
                            + visualizer.textPadding + 12 - textDistance) / 12)) * (1 - root.visualizerMix)
                    opacity: (0.24 + level * 0.76 * visualizer.activity) * (1 - quietMix * 0.92)
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
            id: currentLabel
            upcoming: lineSurface.upcoming
            objectName: "bar-lyrics-text"
            text: lineSurface.displayedText
            opacity: lineSurface.progress * (1 - root.visualizerMix)
            transform: Translate { y: 4 * (1 - lineSurface.progress) }
        }
        StandardProgressBar {
            id: lineProgressTrack
            objectName: "bar-lyrics-line-progress"
            // Follow the visible label width, including when long lyrics elide.
            width: Math.max(0, Math.min(currentLabel.contentWidth, currentLabel.width))
            height: 2
            radius: height / 2
            x: currentLabel.x + (currentLabel.width - width) / 2
            y: Math.min(lineSurface.height - height - 2,
                (lineSurface.height + currentLabel.implicitHeight) / 2 + 2)
            visible: !lineSurface.upcoming && root.currentText !== "" && root.displayLines.length > 0
                && root.lyricPosition >= root.lineStart
            opacity: currentLabel.opacity
            value: root.lineProgress
            activeColor: BarAppearance.activeColor
            foregroundColor: BarAppearance.foregroundColor
            fillObjectName: "bar-lyrics-line-progress-fill"
        }
    }
    Line { id: currentPanel; objectName: "bar-lyrics-current"; x: root.edgeMargin; lyric: (root.estimatedTiming && root.currentText ? "≈ " : "") + root.currentText }
    Line { id: nextPanel; objectName: "bar-lyrics-next"; x: root.width - root.sideWidth - root.edgeMargin; lyric: (root.estimatedTiming && root.nextText ? "≈ " : "") + root.nextText; upcoming: true }
    StyledRect {
        id: calibrationPanel
        parent: root.calibrationParent
        objectName: "lyrics-calibration-panel"
        visible: root.visible && root.estimatedTiming && root.calibrationOpen
        x: root.inlineMode ? (parent.width - width) / 2 : root.width - width - root.gap
        y: root.stripHeight + 8
        width: Math.min(520, parent.width - root.gap * 2)
        height: Math.max(0, Math.min(460, parent.height - y - 12))
        z: 10
        variant: "popup"
        radius: Styling.radius(0)
        onVisibleChanged: if (visible) Qt.callLater(() => calibrationLines.positionViewAtIndex(root.lineIndex, ListView.Center))
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                StyledText { text: "Align lyrics"; font.bold: true; Layout.fillWidth: true }
                ThemeButton { text: "Close"; onClicked: root.calibrationOpen = false }
            }
            StyledText {
                text: "Tap the line being sung right now."
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Colors.overSurfaceVariant
            }
            ListView {
                id: calibrationLines
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 4
                model: root.displayLines
                delegate: ThemeButton {
                    required property var modelData
                    required property int index
                    objectName: "lyrics-calibrate-line-" + index
                    width: calibrationLines.width
                    text: (index + 1) + "  " + modelData.text
                    highlighted: index === root.lineIndex
                    Accessible.name: "Align to " + modelData.text
                    onClicked: root.calibrateLine(index)
                }
                ScrollBar.vertical: ScrollBar {}
            }
        }
    }

}
