pragma ComponentBehavior: Bound
import QtQuick
import "TypingTexts.js" as TypingTexts
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.modules.components
import qs.modules.theme

Item {
    id: root
    signal backRequested()
    property bool practicing: false
    property bool filePickerActive: false
    property bool resumeOnOpen: false
    property string bookId: ""
    property string bookTitle: ""
    property int bookLength: 0
    property int position: 0
    property int rounds: 0
    property string passage: ""
    property var chapters: []
    property var library: []
    property bool backendStarted: false
    property bool ready: false
    property bool busy: false
    property bool dirty: false
    property bool restoring: false
    property bool draft: false
    property string draftTitle: "Pasted text"
    property int requestId: 0
    property int pageRequest: 0
    property var queued: []
    property string errorMessage: ""
    readonly property string chapterTitle: {
        let title = "Beginning";
        for (const chapter of chapters) { if (chapter.position > position) break; title = chapter.title; }
        return title;
    }
    property string message: "Import a book, resume your library, or choose a practice text."
    function characters(value) {
        return value.match(/[\uD800-\uDBFF][\uDC00-\uDFFF]|[\s\S]/g) ?? [];
    }
    readonly property real progress: bookLength ? Math.min(1, (position + characters(answer.text).length) / bookLength) : 0
    readonly property var passageWords: {
        let words = [];
        let start = 0;
        for (const token of passage.match(/\S+\s*|\s+/g) ?? []) {
            // Keep ordinary words together while bounding unusually long tokens.
            let tokenStart = start;
            const letters = characters(token);
            for (let offset = 0; offset < letters.length; offset += 36) {
                const wordText = letters.slice(offset, offset + 36).join("");
                words.push({text: wordText, start: tokenStart});
                tokenStart += wordText.length;
            }
            start += token.length;
        }
        return words;
    }
    implicitHeight: practicing ? 240 : 500
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
    onVisibleChanged: {
        if (visible) { reveal(); backendStarted = true; if (ready) send({action: "list"}, false); }
        else saveProgress();
        if (visible && practicing) Qt.callLater(() => answer.forceActiveFocus());
    }
    Component.onCompleted: { if (visible) backendStarted = true; }
    function send(data, page = true) {
        data.request = ++requestId;
        if (page) { pageRequest = data.request; busy = true; errorMessage = ""; }
        if (ready) backend.write(JSON.stringify(data) + "\n");
        else { queued = queued.concat([data]); backendStarted = true; }
    }
    function saveProgress() {
        if (!dirty || !bookId || busy || restoring) return;
        dirty = false;
        send({action: "save", id: bookId, position: position, typed: answer.text, loops: rounds}, false);
    }
    function openBook(id) {
        if (busy) return;
        saveProgress(); draft = false;
        send({action: "open", id: id});
    }
    function seek(offset) {
        if (!bookId || busy) return;
        dirty = false;
        send({action: "seek", id: bookId, position: Math.max(0, Math.min(bookLength - 1, offset)), typed: "", loops: rounds});
    }
    function receive(line) {
        try {
            const data = JSON.parse(line);
            if (data.action === "list") { if (data.books) library = data.books; return; }
            if (data.error) { if (data.request === pageRequest) busy = false; if (data.action === "save") dirty = true; message = data.error; errorMessage = data.error; return; }
            if (data.request !== pageRequest || !data.passage) return;
            restoring = true;
            bookId = data.id; bookTitle = data.title; bookLength = data.length;
            position = data.position; rounds = data.loops; if (data.chapters) chapters = data.chapters;
            passage = data.passage; answer.text = data.typed; answer.cursorPosition = answer.length;
            dirty = false; draft = false; busy = false; restoring = false;
            message = "Ready to resume. Your place is saved on this device.";
            if (data.action === "add") { paste.text = ""; practicing = true; }
            if (data.action === "import") { paste.text = ""; practicing = false; }
            if (data.action === "open" && resumeOnOpen) { resumeOnOpen = false; practicing = true; }
            if (practicing && visible) Qt.callLater(() => answer.forceActiveFocus());
            if (data.action !== "next") send({action: "list"}, false);
        } catch (error) { busy = false; message = "Could not read the book service response."; }
    }
    Timer { id: saveDelay; interval: 650; onTriggered: root.saveProgress() }
    Timer { interval: 5000; running: root.backendStarted; repeat: true; onTriggered: root.saveProgress() }

    function status() {
        return JSON.stringify({practicing: practicing, textLength: bookLength,
            typed: answer.text.length, position: position, rounds: rounds,
            presets: TypingTexts.passages.length, message: message, busy: busy,
            title: bookTitle, chapters: chapters.length, library: library.length, filePickerActive: filePickerActive});
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
        if (busy || index < 0 || index >= TypingTexts.passages.length) return;
        saveProgress();
        paste.text = TypingTexts.passages[index].text;
        draftTitle = TypingTexts.passages[index].title;
        draft = true; practicing = false;
        message = draftTitle + " loaded. Choose Start practice.";
    }
    function showLibrary() {
        saveProgress();
        practicing = false;
    }
    function goBack() {
        if (busy || filePickerActive) return;
        if (practicing) { showLibrary(); return; }
        if (bookId) { practicing = true; answer.forceActiveFocus(); }
        else if (draft) start();
        else if (library.length) { resumeOnOpen = true; openBook(library[0].id); }
    }
    function openImport() {
        if (busy || filePickerActive) return;
        showLibrary();
        filePickerActive = true;
        // Commit the focus/mask release before mapping the external file chooser.
        pickerLaunch.restart();
    }
    Keys.onEscapePressed: event => { root.goBack(); event.accepted = true; }
    function start() {
        if (busy) return;
        if (draft || !bookId) {
            if (!paste.text.trim().length) { message = "Add some text or import a book first."; return; }
            send({action: "add", title: draftTitle, text: paste.text});
        } else { practicing = true; answer.forceActiveFocus(); }
    }
    function advance() {
        if (restoring || busy || !bookId) return;
        if (characters(answer.text).length > 90) {
            answer.text = characters(answer.text).slice(0, 90).join("");
            answer.cursorPosition = answer.length;
            return;
        }
        dirty = true; saveDelay.restart();
        if (!passage.length || answer.text !== passage) return;
        const next = position + characters(passage).length;
        dirty = false;
        send({action: "next", id: bookId, position: next >= bookLength ? 0 : next,
            typed: "", loops: rounds + (next >= bookLength ? 1 : 0)});
    }
    Timer {
        id: pickerLaunch
        interval: 100
        onTriggered: { pickerProcess.running = true; pickerWatchdog.restart(); }
    }
    Timer {
        id: pickerWatchdog
        interval: 2000
        onTriggered: {
            if (root.filePickerActive && !pickerProcess.running) {
                root.filePickerActive = false;
                root.message = "Could not open the file chooser. Check that Zenity is installed.";
            }
        }
    }
    Process {
        id: pickerProcess
        command: ["zenity", "--file-selection", "--title=Import EPUB or PDF",
            "--file-filter=Books | *.epub *.EPUB *.pdf *.docx *.odt *.html *.htm *.xml *.txt *.md *.csv *.json *.log",
            "--file-filter=All files | *"]
        onStarted: pickerWatchdog.stop()
        stdout: StdioCollector {
            onStreamFinished: {
                const path = text.replace(/\r?\n$/, "");
                if (path.length) root.send({action: "import", path: path});
            }
        }
        onExited: (exitCode, exitStatus) => {
            pickerWatchdog.stop();
            root.filePickerActive = false;
            if (exitCode > 1) root.message = "The file chooser could not open. Try Import again.";
        }
    }
    Process {
        id: backend
        command: ["python3", "-B", decodeURIComponent(Qt.resolvedUrl("scripts/typing_books.py").toString().replace("file://", ""))]
        stdinEnabled: true
        running: root.backendStarted
        onStarted: {
            root.ready = true;
            for (const data of root.queued) backend.write(JSON.stringify(data) + "\n");
            root.queued = [];
            root.send({action: "list"}, false);
        }
        stdout: SplitParser { onRead: line => root.receive(line) }
        onExited: {
            root.ready = false; root.backendStarted = false; root.busy = false;
            root.message = "Book service stopped. Reopen typing to reconnect."; root.errorMessage = root.message;
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
                Layout.maximumHeight: 36
                StyledText { text: root.practicing ? root.bookTitle : "Your book library"; elide: Text.ElideRight; Layout.minimumWidth: 0; font.pixelSize: 18; opacity: 0.65; Layout.fillWidth: true }
                TextButton { objectName: "typing-library"; visible: root.practicing; text: "Library"; onClicked: root.showLibrary() }
                TextButton { visible: root.practicing; text: "Import"; enabled: !root.busy; onClicked: root.openImport() }
                TextButton { objectName: "typing-back"; visible: !root.practicing; text: "Back"; enabled: !root.busy && (root.bookId.length > 0 || root.draft || root.library.length > 0); onClicked: root.goBack() }
                TextButton { text: "Close"; onClicked: { root.saveProgress(); root.backRequested(); } }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12
                StyledText { visible: !root.practicing; opacity: 0.55; text: root.message; Layout.fillWidth: true; wrapMode: Text.Wrap }
                RowLayout {
                    visible: !root.practicing
                    TextButton { text: root.busy ? "Loading…" : "Import EPUB / PDF"; objectName: "typing-import"; enabled: !root.busy; onClicked: root.openImport() }
                    TextButton { text: "Paste text"; enabled: !root.busy; onClicked: { root.saveProgress(); root.draft = true; root.draftTitle = "Pasted text"; paste.text = ""; paste.forceActiveFocus(); } }
                    TextButton { text: root.bookId && !root.draft ? "Resume" : "Start practice"; enabled: !root.busy; onClicked: root.start() }
                }
                ComboBox {
                    visible: !root.practicing && root.library.length > 0
                    Layout.fillWidth: true
                    model: root.library
                    textRole: "title"
                    currentIndex: -1
                    displayText: currentIndex < 0 ? "Resume a saved book…" : currentText
                    onActivated: index => root.openBook(root.library[index].id)
                }
                RowLayout {
                    visible: !root.practicing && root.bookId.length > 0 && !root.draft
                    Layout.fillWidth: true
                    ComboBox {
                        Layout.fillWidth: true
                        model: root.chapters
                        textRole: "title"
                        displayText: "Jump to chapter…"
                        onActivated: index => root.seek(root.chapters[index].position)
                    }
                    StyledText { opacity: 0.6; text: (root.progress * 100).toFixed(1) + "%" }
                }
                Slider {
                    id: bookPositionSlider
                    objectName: "typing-book-position"
                    visible: !root.practicing && root.bookId.length > 0 && !root.draft
                    Layout.fillWidth: true
                    from: 0; to: Math.max(1, root.bookLength - 1)
                    value: root.position
                    onMoved: jumpDelay.restart()
                    Timer { id: jumpDelay; interval: 250; onTriggered: root.seek(Math.round(bookPositionSlider.value)) }
                    ToolTip.visible: hovered || pressed
                    ToolTip.text: "Book position · " + (100 * value / Math.max(1, root.bookLength)).toFixed(1) + "%"
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
                    visible: !root.practicing && (root.draft || !root.bookId) && !presets.popup.visible
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    TextArea {
                        id: paste
                        placeholderText: "Paste a book or text here, or import EPUB / PDF…"
                        onTextChanged: { if (activeFocus && !root.restoring) { root.draft = true; root.draftTitle = "Pasted text"; } }
                        background: Item {}
                        placeholderTextColor: Qt.alpha(Colors.overSurface, 0.35)
                        wrapMode: TextEdit.Wrap
                        color: Colors.overSurface
                        font.family: "JetBrains Mono"
                        font.pixelSize: 14
                    }
                }
                Item {
                    visible: !root.practicing && !root.draft && root.bookId.length > 0
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }
                ColumnLayout {
                    visible: root.practicing
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
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
                                        model: root.characters(word.modelData.text)
                                        delegate: StyledText {
                                            id: glyph
                                            required property int index
                                            required property string modelData
                                            readonly property bool typed: characterIndex < answer.text.length
                                            property bool initialized: false
                                            property real lift: 0
                                            property real zoom: 1
                                            property real shine: 0
                                            property real entrance: 1
                                            scale: zoom
                                            transform: Translate { y: glyph.lift + (1 - glyph.entrance) * 7 }
                                            onTypedChanged: {
                                                if (!initialized) return;
                                                if (typed && Motion.enabled && visible) letterPop.restart();
                                                else { letterPop.stop(); lift = 0; zoom = 1; shine = 0; }
                                            }
                                            Component.onCompleted: { initialized = true; if (Motion.enabled && visible) entranceAnimation.start(); }
                                            onVisibleChanged: { if (initialized && visible && Motion.enabled) entranceAnimation.restart(); }
                                            SequentialAnimation {
                                                id: entranceAnimation
                                                PauseAnimation { duration: Math.min(glyph.characterIndex, 24) * 7 }
                                                NumberAnimation { target: glyph; property: "entrance"; from: 0; to: 1; duration: Motion.enter; easing.type: Easing.OutCubic }
                                            }
                                            ParallelAnimation {
                                                id: letterPop
                                                NumberAnimation { target: glyph; property: "lift"; from: -4; to: 0; duration: Motion.enter; easing.type: Easing.OutBack }
                                                NumberAnimation { target: glyph; property: "zoom"; from: 1.12; to: 1; duration: Motion.enter; easing.type: Easing.OutBack }
                                                NumberAnimation { target: glyph; property: "shine"; from: 1; to: 0; duration: Motion.base; easing.type: Easing.OutCubic }
                                            }
                                            readonly property int characterIndex: word.modelData.start + root.characters(word.modelData.text).slice(0, index).join("").length
                                            objectName: "typing-character-" + characterIndex
                                            text: modelData === " " ? "\u00a0" : modelData
                                            textFormat: Text.PlainText
                                            font.family: "JetBrains Mono"
                                            font.pixelSize: 22
                                            font.underline: characterIndex === answer.text.length
                                            lineHeight: 1.45
                                            opacity: (typed ? 1 : 0.28) * entrance
                                            Behavior on opacity {
                                                enabled: Motion.enabled
                                                NumberAnimation { duration: Math.round(Motion.base * 0.45); easing.type: Easing.OutCubic }
                                            }
                                            color: typed ? (answer.text.substr(characterIndex, modelData.length) !== modelData ? Colors.error : Qt.tint(Colors.overSurface, Qt.alpha(Colors.primary, shine * 0.65))) : Colors.overSurface

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
                            readOnly: root.busy
                            onTextChanged: root.advance()
                            Keys.onEscapePressed: event => { root.goBack(); event.accepted = true; }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: root.errorMessage || root.chapterTitle; opacity: 0.5; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true; Layout.minimumWidth: 0 }
                        StyledText { text: (root.progress * 100).toFixed(1) + "%"; opacity: 0.5; font.pixelSize: 11 }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 2
                        radius: 1
                        color: Qt.alpha(Colors.overSurface, 0.08)
                        Rectangle {
                            height: parent.height
                            width: parent.width * root.progress
                            radius: 1
                            color: Qt.alpha(Colors.primary, 0.65)
                            Behavior on width { enabled: Motion.enabled; NumberAnimation { duration: Motion.enter; easing.type: Easing.OutCubic } }
                        }
                    }

                }
            }
        }
    }
}
