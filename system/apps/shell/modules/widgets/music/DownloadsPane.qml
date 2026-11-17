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
    property bool mixTracks: false
    property string audioFormat: "ogg"
    readonly property bool canDownload: !busy && service.running && folder.text.trim().length > 0 && links.text.trim().length > 0
    spacing: 16
    signal completed()
    function prepareMix(data) {
        if (busy) return false;
        links.text = data.links; folder.text = data.folder; mixTracks = true;
        status = "Spotify playlist ready · downloads its current contents";
        return true;
    }
    function start() {
        if (!canDownload) return;
        busy = true; failed = false; cancelling = false;
        status = "Downloading…";
        logText = "Starting…\n";
        service.write(JSON.stringify({backend: "spotdl", mode: 0,
            links: links.text, folder: folder.text, format: audioFormat, mixTracks: mixTracks}) + "\n");
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
                if (message.error) { root.busy = !!message.busy; root.failed = true; root.status = message.busy ? "Download still running" : "Could not start"; root.logText += message.error + "\n"; }
                if (message.done) {
                    const wasCancelled = message.cancelled === true || root.cancelling;
                    root.busy = false;
                    root.logText += wasCancelled ? "Cancelled.\n" : message.code === 0 ? "Finished · check log for skipped items.\n" : "Stopped or failed · see log.\n";
                    root.failed = message.code !== 0 && !wasCancelled;
                    root.status = wasCancelled ? "Cancelled" : message.code !== 0 ? "Needs attention" : "Finished";
                    root.completed();
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
        ThemeButton { objectName: "music-download-start"; text: root.busy ? root.status : "Start download"; enabled: root.canDownload; highlighted: true; onClicked: root.start() }
        ThemeButton { objectName: "music-download-cancel"; text: root.cancelling ? "Cancelling…" : "Cancel"; visible: root.busy; enabled: !root.cancelling; onClicked: { root.cancelling = true; root.status = "Cancelling…"; service.write('{"cancel":true}\n'); } }
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
                    StyledText {
                        Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Colors.overSurfaceVariant
                        text: "spotDL matches Spotify links to YouTube audio. No Spotify sign-in needed."
                    }
                    StyledText { text: "Spotify links"; font.bold: true }
                    SearchInput {
                        id: links; objectName: "music-download-links"
                        Layout.fillWidth: true
                        placeholderText: "Paste track, album or playlist links"; enabled: !root.busy
                        onSearchTextChanged: text => { root.mixTracks = false; }
                    }
                    StyledText { text: "Separate multiple links with spaces."; color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-2) }
                }
            }
            StyledRect {
                variant: "pane"; Layout.fillWidth: true; implicitHeight: destination.implicitHeight + 40
                ColumnLayout {
                    id: destination
                    anchors.fill: parent; anchors.margins: 20; spacing: 12
                    StyledText { text: "02  Save to your library"; font.bold: true; font.pixelSize: Styling.fontSize(2) }
                    StyledText { text: "Destination folder" }
                    SearchInput { id: folder; Layout.fillWidth: true; text: "~/Music"; enabled: !root.busy && !root.mixTracks }
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
                        id: activityScroll
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        function scrollToBottom() {
                            contentItem.contentY = Math.max(0, contentItem.contentHeight - contentItem.height);
                        }
                        TextArea {
                            text: root.logText; placeholderText: "Download output will appear here."
                            onTextChanged: Qt.callLater(activityScroll.scrollToBottom)
                            onContentHeightChanged: Qt.callLater(activityScroll.scrollToBottom)
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
