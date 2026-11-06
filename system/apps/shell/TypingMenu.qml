pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.modules.components
import qs.modules.theme
import qs.modules.globals

PanelWindow {
    id: root
    property bool opened: false
    property bool practicing: false
    property string sourceText: ""
    property int position: 0
    property int rounds: 0
    property string message: "Paste text or import a document. Practice at your own pace."
    readonly property string passage: sourceText.slice(position, position + 160)
    anchors { top: true; right: true }
    margins { top: 8; right: 18 }
    implicitWidth: opened ? Math.min(720, screen.width - 36) : 110
    implicitHeight: opened ? Math.min(570, screen.height - 40) : 36
    visible: !GlobalStates.lockscreenVisible
    color: "transparent"
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "rebos-shell-typing"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: opened ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    function start() {
        let value = paste.text.replace(/\s+/g, " ").trim();
        if (!value.length) { message = "Add some text first."; return; }
        sourceText = value; position = 0; rounds = 0;
        practicing = true; answer.text = ""; answer.forceActiveFocus();
        message = "Keep going. There is no timer or failure.";
    }
    function advance() {
        if (answer.text !== passage) return;
        position += passage.length;
        if (position >= sourceText.length) { position = 0; rounds++; }
        answer.text = "";
    }
    IpcHandler {
        target: "typing"
        function toggle(): void { root.opened = !root.opened; }
        function close(): void { root.opened = false; }
    }
    FileDialog {
        id: picker
        title: "Import practice text"
        nameFilters: ["Documents (*.pdf *.docx *.odt *.html *.htm *.xml *.txt *.md *.csv *.json *.log)", "All files (*)"]
        onAccepted: {
            importer.command = ["python3", Qt.resolvedUrl("scripts/typing_import.py").toString().replace("file://", ""), selectedFile.toString()];
            importer.running = true;
        }
    }
    Process {
        id: importer
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    let result = JSON.parse(text);
                    if (result.error) root.message = result.error;
                    else { paste.text = result.text; root.practicing = false; root.message = "Text imported. Choose Start practice."; }
                } catch (e) { root.message = "Could not import this document."; }
            }
        }
    }
    Rectangle {
        anchors.fill: parent
        radius: 16
        color: Qt.alpha(Colors.surfaceContainer, 0.82)
        border.color: Qt.alpha(Colors.outline, 0.45)
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.opened ? 18 : 0
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: root.opened ? "Typing ▴" : "Typing ▾"
                    Layout.fillWidth: true
                    onClicked: root.opened = !root.opened
                }
                Button { visible: root.opened; text: "Close"; onClicked: root.opened = false }
            }
            ColumnLayout {
                visible: root.opened
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12
                StyledText { text: "Continuous typing"; font.pixelSize: 20 }
                StyledText { text: root.message; Layout.fillWidth: true; wrapMode: Text.Wrap }
                RowLayout {
                    Button { text: importer.running ? "Importing…" : "Import document"; enabled: !importer.running; onClicked: picker.open() }
                    Button { text: root.practicing ? "Edit text" : "Start practice"; onClicked: { if (root.practicing) root.practicing = false; else root.start(); } }
                }
                ScrollView {
                    visible: !root.practicing
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    TextArea {
                        id: paste
                        placeholderText: "Paste your text here…"
                        wrapMode: TextEdit.Wrap
                        color: Colors.overSurface
                        font.family: "JetBrains Mono"
                        font.pixelSize: 14
                    }
                }
                ColumnLayout {
                    visible: root.practicing
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    StyledText {
                        text: root.passage
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        font.family: "JetBrains Mono"
                        font.pixelSize: 20
                        lineHeight: 1.5
                    }
                    StyledText { text: "Character " + (root.position + answer.text.length) + " / " + root.sourceText.length + " · Loops " + root.rounds }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        TextArea {
                            id: answer
                            placeholderText: "Type the passage above…"
                            wrapMode: TextEdit.Wrap
                            font.family: "JetBrains Mono"
                            font.pixelSize: 18
                            color: root.passage.startsWith(text) ? Colors.overSurface : Colors.error
                            onTextChanged: root.advance()
                        }
                    }
                    StyledText { text: root.passage.startsWith(answer.text) ? "Take your time. Every completed passage continues automatically." : "A small mismatch — backspace whenever you like."; Layout.fillWidth: true; wrapMode: Text.Wrap }
                }
            }
        }
    }
}
