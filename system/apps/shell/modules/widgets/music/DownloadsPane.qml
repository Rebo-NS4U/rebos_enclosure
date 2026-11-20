pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Dialogs
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.config
import qs.modules.components
import qs.modules.theme

ColumnLayout {
    id: root
    objectName: "music-downloads"
    property bool settingsReady: false
    property bool restoringSettings: false
    property bool busy: false
    property string logText: ""
    property string status: "Ready"
    property bool failed: false
    property bool cancelling: false
    property bool syncPlaylist: false
    property bool mixTracks: false
    property int parallelTracks: 4
    property string manualFolder: "~/Music"
    property bool preparing: false
    property string audioFormat: "ogg"
    readonly property bool canDownload: settingsReady && !busy && service.running && folder.text.trim().length > 0 && links.text.trim().length > 0
    spacing: 16
    signal completed()
    signal rejected()
    function prepare(data) {
        preparing = true;
        if (!mixTracks) manualFolder = folder.text;
        links.text = data.links;
        folder.text = data.folder;
        mixTracks = true;
        syncPlaylist = data.syncPlaylist === true;
        preparing = false;
        failed = false;
    }
    function prepareSuggestion(data) {
        if (busy || !service.running || !settingsReady) return false;
        prepare(data);
        status = "Downloading Spotify suggestion";
        return true;
    }
    function prepareMix(data) {
        if (busy) return false;
        prepare(data);
        status = syncPlaylist ? "Ready to sync" : "Playlist ready";
        return true;
    }
    function start() {
        if (!canDownload) return;
        busy = true; failed = false; cancelling = false;
        status = "Downloading…";
        logText = "Starting…\n";
        service.write(JSON.stringify({backend: "spotdl", mode: 0,
            threads: parallelTracks, links: links.text, folder: folder.text, format: audioFormat, cookieFile: cookieFile.text.trim(), mixTracks: mixTracks, syncPlaylist: syncPlaylist}) + "\n");
    }
    FolderDialog {
        id: destinationPicker
        title: "Choose download folder"
        onAccepted: folder.text = decodeURIComponent(selectedFolder.toString().replace(/^file:\/\//, ""))
    }
    FileDialog {
        id: cookiePicker
        title: "Choose YouTube cookies.txt"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Cookie files (*.txt)", "All files (*)"]
        onAccepted: cookieFile.text = decodeURIComponent(selectedFile.toString().replace(/^file:\/\//, ""))
    }
    Process {
        id: service
        running: true; stdinEnabled: true
        onStarted: write('{"settingsGet":true}\n')
        command: ["python3", "-u", Qt.resolvedUrl("../../../scripts/music_downloads/service.py").toString().replace("file://", "")]
        stdout: SplitParser {
            onRead: data => {
                let message;
                try { message = JSON.parse(data); } catch (e) { return; }
                if (message.settings) {
                    if (!root.settingsReady) {
                        root.restoringSettings = true;
                        cookieFile.text = message.settings.cookieFile || "";
                        root.restoringSettings = false;
                        root.settingsReady = true;
                    }
                }
                if (message.log) root.logText = (root.logText + message.log + "\n").slice(-60000);
                if (message.error) { root.busy = !!message.busy; root.failed = true; root.status = message.busy ? "Download still running" : "Could not start"; root.logText += message.error + "\n"; if (!message.busy) root.rejected(); }
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
        onExited: { root.busy = false; root.failed = true; root.status = "Service unavailable"; root.logText += "Download service stopped.\n"; root.rejected(); }
    }
    RowLayout {
        Layout.fillWidth: true
        StyledText { text: "Downloads"; Layout.fillWidth: true; font.pixelSize: Styling.fontSize(14); font.bold: true }
        StyledRect {
            variant: root.failed ? "focus" : "common"
            implicitWidth: statusLabel.implicitWidth + 28; implicitHeight: 36
            StyledText { id: statusLabel; anchors.centerIn: parent; text: root.status; color: root.failed ? Colors.error : Colors.primary }
        }
        ThemeButton { objectName: "music-download-start"; visible: !root.busy; text: root.syncPlaylist ? "Sync playlist" : "Start download"; enabled: root.canDownload; highlighted: true; onClicked: root.start() }
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
                    StyledText { text: "Spotify links"; font.bold: true; font.pixelSize: Styling.fontSize(2) }
                    StyledText {
                        Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Colors.overSurfaceVariant
                        text: "spotDL matches Spotify links to YouTube audio. No Spotify sign-in needed."
                    }
                    SearchInput {
                        id: links; objectName: "music-download-links"
                        Layout.fillWidth: true
                        placeholderText: "Paste track, album, artist or playlist links"; enabled: !root.busy
                        onSearchTextChanged: {
                            if (root.mixTracks && !root.preparing) {
                                root.mixTracks = false;
                                root.syncPlaylist = false;
                                folder.text = root.manualFolder;
                                root.status = "Ready";
                            }
                        }
                    }
                    StyledText { text: "Separate multiple links with spaces."; color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-2) }

                }
            }
            StyledRect {
                variant: "pane"; Layout.fillWidth: true; implicitHeight: destination.implicitHeight + 40
                ColumnLayout {
                    id: destination
                    anchors.fill: parent; anchors.margins: 20; spacing: 12
                    StyledText { text: "Save to library"; font.bold: true; font.pixelSize: Styling.fontSize(2) }
                    StyledText { text: "Destination folder" }
                    RowLayout {
                        Layout.fillWidth: true
                        SearchInput { id: folder; objectName: "music-download-folder"; Layout.fillWidth: true; text: "~/Music"; enabled: !root.busy && !root.mixTracks }
                        ThemeButton { text: "Browse"; enabled: folder.enabled; onClicked: destinationPicker.open() }
                    }
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
                    StyledText { Layout.fillWidth: true; text: root.syncPlaylist ? "Sync mirrors Spotify playlist membership. Removed songs stay in your music folder." : "Existing audio files are skipped."; wrapMode: Text.WordWrap; color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-2) }
                    ThemeButton {
                        id: options
                        objectName: "music-download-options"
                        text: checked ? "Hide download options" : "More download options"
                        checkable: true
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: options.checked
                        StyledText { text: "Parallel tracks" }
                        RowLayout {
                            Repeater {
                                model: [1, 2, 4]
                                delegate: ThemeButton {
                                    required property int modelData
                                    objectName: "music-download-workers-" + modelData
                                    text: String(modelData)
                                    Accessible.name: modelData + " parallel tracks"
                                    checked: root.parallelTracks === modelData
                                    enabled: !root.busy
                                    onClicked: root.parallelTracks = modelData
                                }
                            }
                        }
                        StyledText { text: "YouTube cookie file (optional)"; font.bold: true }
                        RowLayout {
                            Layout.fillWidth: true
                            SearchInput {
                                id: cookieFile; objectName: "music-download-cookie-file"
                                Layout.fillWidth: true
                                placeholderText: "Path to exported cookies.txt"
                                enabled: !root.busy && root.settingsReady
                                onTextChanged: if (root.settingsReady && !root.restoringSettings) {
                                    service.write(JSON.stringify({settingsCookieFile: text.trim()}) + "\n");
                                }
                            }
                            ThemeButton { text: "Browse"; enabled: !root.busy && root.settingsReady; onClicked: cookiePicker.open() }
                            ThemeButton { text: "Clear"; enabled: !root.busy && cookieFile.text.length > 0; onClicked: cookieFile.clear() }
                        }
                        StyledText {
                            Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Colors.overSurfaceVariant
                            font.pixelSize: Styling.fontSize(-2)
                            text: "Choose a private Netscape cookies.txt export for audio that requires YouTube sign-in. Music remembers the path until you clear it."
                        }
                    }

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
