pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.services
import qs.modules.theme

StyledRect {
    id: root
    visible: LyricsService.hasLyrics
    readonly property bool requested: (parent?.visible ?? true) && (Window.window?.visible ?? true)
    property bool compact: false
    property bool autoHideControls: true
    property bool idle: false
    readonly property bool controlsVisible: !compact || !autoHideControls || !idle

    function revealControls() {
        idle = false;
        if (compact && autoHideControls && visible) idleTimer.restart();
        else idleTimer.stop();
    }
    onAutoHideControlsChanged: revealControls()
    onCompactChanged: revealControls()
    variant: controlsVisible ? "common" : "transparent"
    backgroundOpacity: controlsVisible ? -1 : 0
    enableBorder: controlsVisible
    radius: Styling.radius(0)
    implicitHeight: visible ? content.implicitHeight + 24 : 0
    onVisibleChanged: revealControls()
    // Demand follows the host, not our own visibility: a hidden section must
    // still discover timed lyrics when its menu opens.
    onRequestedChanged: {
        if (!registered) return;
        if (requested) LyricsService.viewers++;
        else LyricsService.viewers = Math.max(0, LyricsService.viewers - 1);
    }
    property bool registered: false
    Component.onCompleted: { registered = true; if (requested) LyricsService.viewers++; revealControls(); }
    Component.onDestruction: { if (registered && requested) LyricsService.viewers = Math.max(0, LyricsService.viewers - 1); }

    Timer {
        id: idleTimer
        interval: 3000
        onTriggered: root.idle = true
    }
    HoverHandler {
        enabled: root.compact
        onHoveredChanged: root.revealControls()
        onPointChanged: root.revealControls()
    }
    Keys.onPressed: event => { root.revealControls(); event.accepted = false; }

    // Keep a small themed surface behind the lyrics when the chrome is hidden.
    // The outer window stays stable, so revealing controls never shifts the text.
    StyledRect {
        objectName: "idle-lyrics-background"
        x: content.x + scroll.x - 6
        y: content.y + scroll.y - 6
        width: scroll.width + 12
        height: scroll.height + 12
        visible: root.compact && !root.controlsVisible
        variant: "common"
        backgroundOpacity: 0.65
        radius: Styling.radius(0)
    }

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: 12
        spacing: Styling.spacing(8)
        RowLayout {
            opacity: root.controlsVisible ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Motion.contentIn } }
            enabled: root.controlsVisible
            Layout.fillWidth: true
            StyledText {
                text: "Lyrics"
                font.bold: true
                font.letterSpacing: 0.8
                Layout.fillWidth: true
            }
            Rectangle {
                visible: LyricsService.hasLyrics
                implicitWidth: syncedLabel.implicitWidth + 20
                implicitHeight: 24
                radius: 12
                color: Styling.withOpacity(Colors.primary, 0.14)
                StyledText {
                    id: syncedLabel
                    anchors.centerIn: parent
                    objectName: "lyrics-timing-badge"
                    text: "● SYNCED"
                    color: Colors.primary
                    font.pixelSize: Styling.fontSize(-3)
                    font.letterSpacing: 1
                }
            }
        }
        Flow {
            opacity: root.controlsVisible ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Motion.contentIn } }
            enabled: root.controlsVisible
            Layout.fillWidth: true
            spacing: Styling.spacing(4)
            ThemeButton {
                text: "Top"
                checked: LyricsService.pinEdge === "top"
                onClicked: LyricsService.pin("top", root.Window.window?.screen?.name)
            }
            ThemeButton {
                text: "Bottom"
                checked: LyricsService.pinEdge === "bottom"
                onClicked: LyricsService.pin("bottom", root.Window.window?.screen?.name)
            }
            ThemeButton { text: "Unpin"; visible: LyricsService.pinEdge !== ""; onClicked: LyricsService.pinEdge = "" }
            ThemeButton {
                visible: root.compact
                text: "Auto-hide"
                checkable: true
                checked: root.autoHideControls
                onClicked: root.autoHideControls = checked
            }
        }
        StyledText {
            Layout.fillWidth: true
            visible: root.compact
            opacity: root.controlsVisible ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Motion.contentIn } }
            text: MprisController.trackTitle || "No media playing"
            elide: Text.ElideRight
        }
        LyricsViewport {
            id: scroll
            objectName: "lyrics-viewport"
            compact: root.compact
            Layout.fillWidth: true
            Layout.preferredHeight: root.compact ? 190 : 210
        }
        RowLayout {
            opacity: root.controlsVisible ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Motion.contentIn } }
            enabled: root.controlsVisible
            Layout.fillWidth: true
            StyledText {
                Layout.fillWidth: true
                text: LyricsService.provider ? LyricsService.provider + " · Synced" : ""
                color: Colors.overSurfaceVariant
                elide: Text.ElideRight
            }
            ThemeButton { text: "Retry"; visible: !LyricsService.plain && !LyricsService.request; onClicked: LyricsService.refresh() }
        }
    }
}
