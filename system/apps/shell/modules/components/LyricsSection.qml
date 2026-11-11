pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.services
import qs.modules.theme

StyledRect {
    id: root
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
    radius: 16
    implicitHeight: content.implicitHeight + 24
    onVisibleChanged: {
        revealControls();
        if (!registered) return;
        if (visible) LyricsService.viewers++;
        else LyricsService.viewers = Math.max(0, LyricsService.viewers - 1);
    }
    // Register once after creation; visibility changes account for hidden menus.
    property bool registered: false
    Component.onCompleted: { registered = true; if (visible) LyricsService.viewers++; revealControls(); }
    Component.onDestruction: { if (registered && visible) LyricsService.viewers = Math.max(0, LyricsService.viewers - 1); }

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

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8
        RowLayout {
            opacity: root.controlsVisible ? 1 : 0
            enabled: root.controlsVisible
            Layout.fillWidth: true
            StyledText { text: "Lyrics"; font.bold: true; Layout.fillWidth: true }
        }
        Flow {
            opacity: root.controlsVisible ? 1 : 0
            enabled: root.controlsVisible
            Layout.fillWidth: true
            spacing: 4
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
            text: MprisController.trackTitle || "No media playing"
            elide: Text.ElideRight
        }
        ScrollView {
            id: scroll
            Layout.fillWidth: true
            Layout.preferredHeight: root.compact ? 80 : 130
            clip: true
            contentWidth: availableWidth
            Text {
                width: scroll.availableWidth
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                text: LyricsService.lines.length
                    ? (LyricsService.currentLine >= 0 ? LyricsService.lines[LyricsService.currentLine].text || "♪" : "♪")
                        + "\n" + (LyricsService.lines[LyricsService.currentLine + 1]?.text || "")
                    : LyricsService.plain || LyricsService.status
                color: Colors.overSurface
                style: root.compact ? Text.Outline : Text.Normal
                styleColor: Colors.scrim
                font: lyricFont.font
                horizontalAlignment: Text.AlignHCenter
            }
        }
        RowLayout {
            opacity: root.controlsVisible ? 1 : 0
            enabled: root.controlsVisible
            Layout.fillWidth: true
            StyledText {
                Layout.fillWidth: true
                text: LyricsService.provider ? LyricsService.provider + (LyricsService.lines.length ? " · Synced" : " · Unsynced") : ""
                color: Colors.overSurfaceVariant
                elide: Text.ElideRight
            }
            ThemeButton { text: "Retry"; visible: !LyricsService.plain && !LyricsService.request; onClicked: LyricsService.refresh() }
        }
    }
    StyledText { id: lyricFont; visible: false }
}
