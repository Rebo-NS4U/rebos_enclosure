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
    readonly property string passage: {
        const chunk = sourceText.slice(position, position + 90);
        const boundary = chunk.lastIndexOf(" ");
        return position + 90 < sourceText.length && boundary > 40 ? chunk.slice(0, boundary + 1) : chunk;
    }
    readonly property var passageWords: {
        let words = [];
        let start = 0;
        for (const token of passage.match(/\S+\s*|\s+/g) ?? []) {
            // Keep ordinary words together while bounding unusually long tokens.
            for (let offset = 0; offset < token.length; offset += 36)
                words.push({text: token.slice(offset, offset + 36), start: start + offset});
            start += token.length;
        }
        return words;
    }
    implicitHeight: practicing ? 220 : 440
    property real revealProgress: 1
    function reveal() {
        if (!Motion.enabled || !visible) { revealProgress = 1; return; }
        revealAnimation.restart();
    }
    NumberAnimation {
        id: revealAnimation
        target: root
        property: "revealProgress"
        from: 0.35
        to: 1
        duration: Math.round(Motion.base * 1.25)
        easing.type: Easing.OutQuint
    }
    onPracticingChanged: reveal()
    onPositionChanged: { if (practicing) reveal(); }
    onVisibleChanged: { if (visible) reveal(); if (visible && practicing) Qt.callLater(() => answer.forceActiveFocus()); }
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
            Behavior on opacity {
                enabled: Motion.enabled
                NumberAnimation { duration: Motion.feedback; easing.type: Easing.OutCubic }
            }
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
        opacity: root.revealProgress
        transform: Translate { y: (1 - root.revealProgress) * 8 }
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                StyledText { text: root.practicing ? "Typing" : "Continuous typing"; font.pixelSize: 18; opacity: 0.65; Layout.fillWidth: true }
                TextButton { visible: root.practicing; text: "Edit"; onClicked: root.practicing = false }
                TextButton { text: "Back"; onClicked: root.backRequested() }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12
                StyledText { visible: !root.practicing; opacity: 0.55; text: root.message; Layout.fillWidth: true; wrapMode: Text.Wrap }
                RowLayout {
                    visible: !root.practicing
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
                                model: root.passageWords
                                delegate: Row {
                                    id: word
                                    required property var modelData
                                    Repeater {
                                        model: word.modelData.text.length
                                        delegate: StyledText {
                                            required property int index
                                            readonly property int characterIndex: word.modelData.start + index
                                            objectName: "typing-character-" + characterIndex
                                            text: root.passage.charAt(characterIndex) === " " ? "\u00a0" : root.passage.charAt(characterIndex)
                                            textFormat: Text.PlainText
                                            font.family: "JetBrains Mono"
                                            font.pixelSize: 22
                                            font.underline: characterIndex === answer.text.length
                                            lineHeight: 1.45
                                            opacity: characterIndex < answer.text.length ? 1 : 0.28
                                            Behavior on opacity {
                                                enabled: Motion.enabled
                                                NumberAnimation { duration: Math.round(Motion.base * 0.45); easing.type: Easing.OutCubic }
                                            }
                                            Behavior on color {
                                                enabled: Motion.enabled
                                                ColorAnimation { duration: Motion.feedback; easing.type: Easing.OutCubic }
                                            }
                                            color: characterIndex < answer.text.length && answer.text[characterIndex] !== root.passage[characterIndex] ? Colors.error : Colors.overSurface
                                        }
                                    }
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
                }
            }
        }
    }
}
