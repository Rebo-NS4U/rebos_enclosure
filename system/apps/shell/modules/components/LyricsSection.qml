pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.services
import qs.modules.theme

StyledRect {
    id: root
    property bool compact: false
    variant: "common"
    radius: 16
    implicitHeight: content.implicitHeight + 24
    onVisibleChanged: {
        if (!registered) return;
        if (visible) LyricsService.viewers++;
        else LyricsService.viewers = Math.max(0, LyricsService.viewers - 1);
    }
    // Register once after creation; visibility changes account for hidden menus.
    property bool registered: false
    Component.onCompleted: { registered = true; if (visible) LyricsService.viewers++; }
    Component.onDestruction: { if (registered && visible) LyricsService.viewers = Math.max(0, LyricsService.viewers - 1); }

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8
        RowLayout {
            Layout.fillWidth: true
            StyledText { text: "Lyrics"; font.bold: true; Layout.fillWidth: true }
        }
        Flow {
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
        }
        StyledText {
            Layout.fillWidth: true
            visible: root.compact
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
                font: lyricFont.font
                horizontalAlignment: Text.AlignHCenter
            }
        }
        RowLayout {
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
