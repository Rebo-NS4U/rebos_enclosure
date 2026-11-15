pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.modules.components
import qs.modules.theme

ColumnLayout {
    id: root
    property bool busy: false
    property string logText: ""
    signal completed()
    function start(login) {
        busy = true; logText = "Starting…\n";
        service.write(JSON.stringify({backend: backend.currentIndex ? "zotify" : "spotdl", mode: mode.currentIndex,
            links: links.text, folder: folder.text, format: format.currentText, login: login}) + "\n");
    }
    Process {
        id: service
        running: true; stdinEnabled: true
        command: ["python3", "-u", Qt.resolvedUrl("../../../scripts/music_downloads/service.py").toString().replace("file://", "")]
        stdout: SplitParser {
            onRead: data => {
                let message;
                try { message = JSON.parse(data); } catch (e) { return; }
                if (message.log) root.logText = (root.logText + message.log + "\n").slice(-60000);
                if (message.error) { root.busy = false; root.logText += message.error + "\n"; }
                if (message.done) {
                    root.busy = false;
                    root.logText += message.code === 0 ? "Finished · check log for skipped items.\n" : "Stopped or failed · see log.\n";
                    root.completed();
                }
            }
        }
        onExited: { root.busy = false; root.logText += "Download service stopped.\n"; }
    }
    StyledText { text: "Downloads"; font.bold: true }
    StyledText { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "spotDL matches Spotify links to YouTube audio. Zotify uses Spotify audio and browser sign-in." }
    RowLayout {
        ComboBox { id: backend; model: ["spotDL", "Zotify"]; enabled: !root.busy; Accessible.name: "Downloader" }
        ComboBox { id: mode; model: ["Links", "Liked songs", "Followed artists"]; enabled: !root.busy && backend.currentIndex === 1; Accessible.name: "Download source" }
        ComboBox { id: format; model: ["mp3", "ogg", "flac", "wav"]; enabled: !root.busy; Accessible.name: "Audio format" }
    }
    StyledText { text: "Spotify links (separate with spaces)" }
    SearchInput { id: links; Layout.fillWidth: true; placeholderText: "https://open.spotify.com/…"; enabled: !root.busy }
    StyledText { text: "Save downloads to" }
    SearchInput { id: folder; Layout.fillWidth: true; text: "~/Music"; enabled: !root.busy }
    RowLayout {
        ThemeButton { text: root.busy ? "Working…" : "Download"; enabled: !root.busy; highlighted: true; onClicked: root.start(false) }
        ThemeButton { text: "Sign in with browser"; visible: backend.currentIndex === 1; enabled: !root.busy; onClicked: root.start(true) }
        ThemeButton { text: "Cancel"; enabled: root.busy; onClicked: service.write('{"cancel":true}\n') }
    }
    ScrollView {
        Layout.fillWidth: true; Layout.fillHeight: true
        TextArea { text: root.logText; readOnly: true; wrapMode: TextEdit.Wrap; color: Colors.overSurface; background: null; selectByMouse: true }
    }
}
