pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.config
import qs.modules.components
import qs.modules.theme

ColumnLayout {
    id: root
    objectName: "music-downloads"
    property bool busy: false
    property string logText: ""
    property string status: "Ready"
    property bool failed: false
    property bool cancelling: false
    property bool loginOnly: false
    property int backendIndex: 0
    property int sourceIndex: 0
    property string audioFormat: "mp3"
    readonly property bool needsLinks: backendIndex === 0 || sourceIndex === 0
    readonly property bool canDownload: !busy && service.running && folder.text.trim().length > 0 && (!needsLinks || links.text.trim().length > 0)
    spacing: 16
    signal completed()
    function start(login) {
        if (busy || (!login && !canDownload)) return;
        busy = true; failed = false; cancelling = false; loginOnly = login;
        status = login ? "Signing in…" : "Downloading…";
        logText = "Starting…\n";
        service.write(JSON.stringify({backend: backendIndex ? "zotify" : "spotdl", mode: backendIndex === 0 ? 0 : sourceIndex,
            links: links.text, folder: folder.text, format: audioFormat, login: login}) + "\n");
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
                if (message.error) { root.busy = false; root.failed = true; root.status = "Could not start"; root.logText += message.error + "\n"; }
                if (message.done) {
                    root.busy = false;
                    root.logText += message.code === 0 ? "Finished · check log for skipped items.\n" : "Stopped or failed · see log.\n";
                    root.failed = message.code !== 0 && !root.cancelling;
                    root.status = root.cancelling ? "Cancelled" : message.code !== 0 ? "Needs attention" : root.loginOnly ? "Signed in" : "Finished";
                    if (message.code === 0 && !root.loginOnly) root.completed();
                }
            }
        }
        onExited: { root.busy = false; root.failed = true; root.status = "Service unavailable"; root.logText += "Download service stopped.\n"; }
    }
    RowLayout {
        Layout.fillWidth: true
        ColumnLayout {
            Layout.fillWidth: true
            StyledText { text: "Downloads"; font.pixelSize: Styling.fontSize(14); font.bold: true }
            StyledText { text: "Bring your music home."; color: Colors.overSurfaceVariant }
        }
        StyledRect {
            variant: root.failed ? "focus" : "common"
            implicitWidth: statusLabel.implicitWidth + 28; implicitHeight: 36
            StyledText { id: statusLabel; anchors.centerIn: parent; text: root.status; color: root.failed ? Colors.error : Colors.primary }
        }
    }
    Flow {
        Layout.fillWidth: true; Layout.preferredHeight: childrenRect.height; spacing: 8
        ThemeButton { objectName: "music-download-start"; text: root.busy ? root.status : "Start download"; enabled: root.canDownload; highlighted: true; onClicked: root.start(false) }
        ThemeButton { text: "Sign in with browser"; visible: root.backendIndex === 1; enabled: !root.busy && service.running; onClicked: root.start(true) }
        ThemeButton { text: root.cancelling ? "Cancelling…" : "Cancel"; visible: root.busy; enabled: !root.cancelling; onClicked: { root.cancelling = true; root.status = "Cancelling…"; service.write('{"cancel":true}\n'); } }
    }
    ScrollView {
        Layout.fillWidth: true; Layout.fillHeight: true
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: parent.width; spacing: 16
            StyledRect {
                variant: "pane"; Layout.fillWidth: true
                implicitHeight: setup.implicitHeight + 40
                ColumnLayout {
                    id: setup
                    anchors.fill: parent; anchors.margins: 20; spacing: 12
                    StyledText { text: "01  Choose your source"; font.bold: true; font.pixelSize: Styling.fontSize(2) }
                    RowLayout {
                        Repeater {
                            model: ["spotDL", "Zotify"]
                            delegate: ThemeButton {
                                required property int index
                                required property string modelData
                                text: modelData; checked: root.backendIndex === index; enabled: !root.busy
                                onClicked: root.backendIndex = index
                            }
                        }
                    }
                    StyledText {
                        Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Colors.overSurfaceVariant
                        text: root.backendIndex === 0 ? "Match Spotify links to YouTube audio. No Spotify sign-in needed." : "Download Spotify audio. Sign in with your browser before your first download."
                    }
                    Flow {
                        Layout.fillWidth: true; Layout.preferredHeight: childrenRect.height; spacing: 8
                        visible: root.backendIndex === 1
                        Repeater {
                            model: ["Links", "Liked songs", "Followed artists"]
                            delegate: ThemeButton {
                                required property int index
                                required property string modelData
                                text: modelData; checked: root.sourceIndex === index; enabled: !root.busy
                                onClicked: root.sourceIndex = index
                            }
                        }
                    }
                    StyledText { visible: root.needsLinks; text: "Spotify links"; font.bold: true }
                    SearchInput {
                        id: links; objectName: "music-download-links"
                        visible: root.needsLinks; Layout.fillWidth: true
                        placeholderText: "Paste track, album or playlist links"; enabled: !root.busy
                    }
                    StyledText { visible: root.needsLinks; text: "Separate multiple links with spaces."; color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-2) }
                }
            }
            StyledRect {
                variant: "pane"; Layout.fillWidth: true; implicitHeight: destination.implicitHeight + 40
                ColumnLayout {
                    id: destination
                    anchors.fill: parent; anchors.margins: 20; spacing: 12
                    StyledText { text: "02  Save to your library"; font.bold: true; font.pixelSize: Styling.fontSize(2) }
                    StyledText { text: "Destination folder" }
                    SearchInput { id: folder; Layout.fillWidth: true; text: "~/Music"; enabled: !root.busy }
                    StyledText { text: "Audio format" }
                    RowLayout {
                        Repeater {
                            model: ["mp3", "ogg", "flac", "wav"]
                            delegate: ThemeButton {
                                required property string modelData
                                text: modelData.toUpperCase(); checked: root.audioFormat === modelData; enabled: !root.busy
                                onClicked: root.audioFormat = modelData
                            }
                        }
                    }
                    StyledText { Layout.fillWidth: true; text: "The format sets the output file type; it cannot improve the source audio quality."; wrapMode: Text.WordWrap; color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-2) }

                }
            }
            StyledRect {
                variant: "pane"; Layout.fillWidth: true; implicitHeight: 260
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 20; spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: "Activity"; font.bold: true; Layout.fillWidth: true }
                        ThemeButton { text: "Clear log"; enabled: !root.busy && root.logText.length > 0; onClicked: root.logText = "" }
                    }
                    ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        TextArea {
                            text: root.logText; placeholderText: "Download output and sign-in instructions will appear here."
                            readOnly: true; wrapMode: TextEdit.Wrap; selectByMouse: true
                            color: Colors.overSurface; placeholderTextColor: Colors.overSurfaceVariant
                            font.family: Config.theme.font; font.pixelSize: Styling.fontSize(-2)
                            selectionColor: Colors.primary; selectedTextColor: Colors.overPrimary
                            background: null
                        }
                    }
                }
            }
        }
    }
}
