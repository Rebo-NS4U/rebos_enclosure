pragma ComponentBehavior: Bound
import QtQuick
import "TypingTexts.js" as TypingTexts
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Quickshell
import Quickshell.Io
import qs.modules.components
import qs.modules.theme

Item {
    id: root
    signal backRequested()
    property bool practicing: false
    property string sourceText: ""
    property int position: 0
    property int rounds: 0
    property string message: "Choose a practice text, paste your own, or import a document."
    readonly property string passage: sourceText.slice(position, position + 160)
    implicitHeight: 520
    onVisibleChanged: { if (visible && practicing) Qt.callLater(() => answer.forceActiveFocus()); }
    function status() {
        return JSON.stringify({practicing: practicing, textLength: paste.text.length,
            typed: answer.text.length, position: position, rounds: rounds,
            presets: TypingTexts.passages.length, message: message});
    }
    component TextButton: Button {
        implicitHeight: 36
        padding: 8
        background: Item {}
        contentItem: StyledText {
            text: parent.text
            opacity: parent.down || parent.activeFocus ? 1 : (parent.hovered ? 0.9 : 0.65)
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.underline: parent.activeFocus
        }
    }
    function loadPreset(index) {
        if (index < 0 || index >= TypingTexts.passages.length) return;
        paste.text = TypingTexts.passages[index].text;
        practicing = false;
        message = TypingTexts.passages[index].title + " loaded. Choose Start practice.";
    }
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
    Item {
        anchors.fill: parent
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                StyledText { text: "Continuous typing"; font.pixelSize: 18; opacity: 0.65; Layout.fillWidth: true }
                TextButton { text: "Back"; onClicked: root.backRequested() }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12
                StyledText { opacity: 0.55; text: root.message; Layout.fillWidth: true; wrapMode: Text.Wrap }
                RowLayout {
                    TextButton { text: importer.running ? "Importing…" : "Import document"; enabled: !importer.running; onClicked: picker.open() }
                    TextButton { text: root.practicing ? "Edit text" : "Start practice"; onClicked: { if (root.practicing) root.practicing = false; else root.start(); } }
                }
                RowLayout {
                    visible: !root.practicing
                    Layout.fillWidth: true
                    StyledText { text: "Practice texts" }
                    ComboBox {
                        id: presets
                        Layout.fillWidth: true
                        model: TypingTexts.passages
                        textRole: "title"
                        background: Item {}
                        contentItem: StyledText {
                            text: presets.displayText
                            opacity: 0.65
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        indicator: Item {}
                        popup: Popup {
                            y: presets.height
                            width: presets.width
                            padding: 0
                            background: Item {}
                            contentItem: Column {
                                Repeater {
                                    model: TypingTexts.passages
                                    delegate: TextButton {
                                        required property int index
                                        required property var modelData
                                        width: presets.width
                                        text: modelData.title
                                        onClicked: {
                                            presets.currentIndex = index;
                                            root.loadPreset(index);
                                            presets.popup.close();
                                        }
                                    }
                                }
                            }
                        }
                        currentIndex: -1
                        displayText: currentIndex < 0 ? "Choose a built-in passage…" : currentText
                        onActivated: index => root.loadPreset(index)
                    }
                }
                StyledText {
                    visible: !root.practicing
                    text: "Original passages · CC0 · Free to copy, change and share"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                ScrollView {
                    background: Item {}
                    visible: !root.practicing && !presets.popup.visible
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    TextArea {
                        id: paste
                        placeholderText: "Paste your text here…"
                        background: Item {}
                        placeholderTextColor: Qt.alpha(Colors.overSurface, 0.35)
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
                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Flow {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            spacing: 0
                            Repeater {
                                model: root.passage.length
                                delegate: StyledText {
                                    required property int index
                                    objectName: "typing-character-" + index
                                    text: root.passage.charAt(index) === " " ? "\u00a0" : root.passage.charAt(index)
                                    textFormat: Text.PlainText
                                    font.family: "JetBrains Mono"
                                    font.pixelSize: 22
                                    font.underline: index === answer.text.length
                                    lineHeight: 1.6
                                    opacity: index < answer.text.length ? 1 : 0.28
                                    color: index < answer.text.length && answer.text[index] !== root.passage[index] ? Colors.error : Colors.overSurface
                                }
                            }
                        }
                        TextEdit {
                            id: answer
                            objectName: "typing-input"
                            anchors.fill: parent
                            color: "transparent"
                            selectionColor: "transparent"
                            selectedTextColor: "transparent"
                            cursorVisible: false
                            wrapMode: TextEdit.Wrap
                            inputMethodHints: Qt.ImhNoPredictiveText
                            onTextChanged: root.advance()
                            Keys.onEscapePressed: event => { root.backRequested(); event.accepted = true; }
                        }
                    }
                    StyledText {
                        opacity: 0.55
                        text: "Character " + (root.position + answer.text.length) + " / " + root.sourceText.length + " · Loops " + root.rounds
                    }
                    StyledText { opacity: 0.55; text: root.passage.startsWith(answer.text) ? "Take your time. Every completed passage continues automatically." : "A small mismatch — backspace whenever you like."; Layout.fillWidth: true; wrapMode: Text.Wrap }
                }
            }
        }
    }
}
