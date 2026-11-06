pragma ComponentBehavior: Bound
import QtQuick
import "TypingTexts.js" as TypingTexts
import "TypingSpeed.js" as TypingSpeed
import "TypingPaging.js" as TypingPaging
import "modules/theme/ShellStyles.js" as ShellStyles
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.modules.components
import qs.modules.theme
import qs.config

Item {
    id: root
    signal backRequested()
    property bool practicing: false
    property bool fullscreen: false
    readonly property int pageLineLimit: fullscreen ? Math.max(2, Math.floor(passageArea.height / (22 * 1.45))) : 2
    onPageLineLimitChanged: fitDelay.restart()
    function toggleFullscreen() {
        fullscreen = !fullscreen;
        fitDelay.restart();
        if (practicing) Qt.callLater(() => answer.forceActiveFocus());
    }
    function handleEscape() {
        if (fullscreen) { fullscreen = false; fitDelay.restart(); if (practicing) answer.forceActiveFocus(); }
        else goBack();
    }
    property bool filePickerActive: false
    property bool resumeOnOpen: false
    property string bookId: ""
    property string bookTitle: ""
    property int bookLength: 0
    property int position: 0
    property int rounds: 0
    property string pageSource: ""
    property var pageLayout: ({text: "", words: [], lines: 0})
    readonly property string passage: pageLayout.text
    property bool turningPage: false
    property string pendingKeys: ""
    property string restoreAction: ""
    property var restoreChapters: []
    property real pageReveal: 1
    property var chapters: []
    property var library: []
    property bool backendStarted: false
    property bool ready: false
    property bool busy: false
    property bool dirty: false
    property bool restoring: false
    property bool draft: false
    property bool samplesExpanded: false
    property string draftKind: "book"
    readonly property var libraryBooks: library.filter(book => book.kind !== "practice")
    property var speedState: TypingSpeed.create()
    property int speedCommitted: 0
    property int speedBaseline: 0
    property double speedNow: Date.now()
    readonly property int liveWpm: TypingSpeed.rate(speedState, speedCommitted + Math.max(0, correctCount() - speedBaseline), speedNow)
    property string draftTitle: "Pasted text"
    property int requestId: 0
    property int pageRequest: 0
    property var queued: []
    property string errorMessage: ""
    readonly property int currentChapterIndex: {
        let result = -1;
        for (let index = 0; index < chapters.length; index++) {
            if (chapters[index].position > position) break;
            result = index;
        }
        return result;
    }
    readonly property string chapterTitle: currentChapterIndex < 0 ? "Beginning" : (chapters[currentChapterIndex].title || "Section " + (currentChapterIndex + 1))
    property string message: "Import a book, resume your library, or choose a practice text."
    function characters(value) {
        return value.match(/[\uD800-\uDBFF][\uDC00-\uDFFF]|[\s\S]/g) ?? [];
    }
    readonly property real progress: bookLength ? Math.min(1, (position + characters(answer.text).length) / bookLength) : 0
    readonly property var passageWords: pageLayout.words
    FontMetrics { id: typingMetrics; font.family: Config.theme.font; font.pixelSize: 22 }
    function characterWidth(text) { return Math.max(1, Math.ceil(typingMetrics.advanceWidth(text))); }
    function fitPage() {
        pageLayout = TypingPaging.layout(pageSource, Math.max(80, root.width - 52), characterWidth, pageLineLimit);
    }
    Timer {
        id: fitDelay
        interval: 150
        onTriggered: { if (!root.restoring && root.pageSource.length) { root.fitPage(); if (root.bookId && root.characters(answer.text).length >= root.characters(root.passage).length) root.advance(); } }
    }
    NumberAnimation {
        id: pageArrival
        target: root
        property: "pageReveal"
        from: 0.25
        to: 1
        duration: Math.max(120, Motion.contentIn)
        easing.type: Easing.OutCubic
    }
    function queueTyping(text) {
        if (turningPage) pendingKeys = characters(pendingKeys + text).slice(0, 4096).join("");
    }
    function undoQueuedKey() {
        if (turningPage) pendingKeys = characters(pendingKeys).slice(0, -1).join("");
    }
    implicitHeight: practicing ? 240 : 600
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
    onPracticingChanged: { reveal(); resetSpeed(); syncCaret(); }
    onVisibleChanged: {
        if (visible) { reveal(); backendStarted = true; if (ready) send({action: "list"}, false); }
        else saveProgress();
        resetSpeed();
        if (visible && practicing) Qt.callLater(() => answer.forceActiveFocus());
    }
    Component.onCompleted: { if (visible) backendStarted = true; }
    function send(data, page = true) {
        data.window = 4096;
        data.request = ++requestId;
        if (page) { pageRequest = data.request; busy = true; errorMessage = ""; }
        if (ready) backend.write(JSON.stringify(data) + "\n");
        else { queued = queued.concat([data]); backendStarted = true; }
    }
    // Follow wallpaper/theme updates once per palette change, not per keystroke.
    property color readingBackground: Colors.background
    readonly property color readingInk: legible(Colors.overSurface, readingBackground, 7)
    readonly property color readingUpcoming: legible(ShellStyles.mix(readingBackground.toString(), readingInk.toString(), 0.55), readingBackground, 4.5)
    readonly property color readingAccent: legible(Colors.primary, readingBackground, 4.5)
    readonly property color readingError: legible(Colors.error, readingBackground, 4.5)
    function outlineFor(color) {
        const value = color.toString();
        return ShellStyles.contrast(value, "#000000") >= ShellStyles.contrast(value, "#ffffff") ? "#000000" : "#ffffff";
    }
    function legible(preferred, background, minimum) {
        const base = Qt.color(background).toString();
        const ink = Qt.color(preferred).toString();
        const endpoint = ShellStyles.contrast("#000000", base) >= ShellStyles.contrast("#ffffff", base) ? "#000000" : "#ffffff";
        const goal = Math.min(minimum, ShellStyles.contrast(endpoint, base));
        for (let step = 0; step <= 20; step++) {
            const candidate = ShellStyles.mix(ink, endpoint, step / 20);
            if (ShellStyles.contrast(candidate, base) >= goal) return candidate;
        }
        return endpoint;
    }
    // Keep input dependencies off the thousands of static glyph delegates.
    property var glyphItems: ({})
    property string renderedInput: ""
    property int renderedCaret: -1
    function updateGlyph(glyph) {
        if (!glyph) return;
        glyph.typed = glyph.characterIndex < answer.text.length;
        glyph.incorrect = glyph.typed && !TypingPaging.matchingCharacter(answer.text.substr(glyph.characterIndex, glyph.modelData.length), glyph.modelData);
        glyph.caretHere = practicing && glyph.characterIndex === Math.min(answer.cursorPosition, passage.length - 1);
    }
    function syncCaret() {
        const previous = renderedCaret;
        renderedCaret = practicing ? Math.min(answer.cursorPosition, passage.length - 1) : -1;
        if (previous !== renderedCaret) {
            updateGlyph(glyphItems[previous]);
            updateGlyph(glyphItems[renderedCaret]);
        }
    }
    function syncGlyphs() {
        const current = answer.text;
        let first = 0;
        const shared = Math.min(current.length, renderedInput.length);
        while (first < shared && current[first] === renderedInput[first]) first++;
        let last = Math.max(current.length, renderedInput.length);
        while (last > first && current[last - 1] === renderedInput[last - 1]) last--;
        for (let index = first; index < last; index++)
            updateGlyph(glyphItems[index]);
        renderedInput = current;
        syncCaret();
    }
    function correctCount() {
        const input = characters(answer.text);
        const target = characters(passage);
        let count = 0;
        for (let index = 0; index < input.length && index < target.length; index++)
            if (TypingPaging.matchingCharacter(input[index], target[index])) count++;
        return count;
    }
    function resetSpeed() {
        speedState = TypingSpeed.create(); speedCommitted = 0;
        speedBaseline = correctCount(); speedNow = Date.now();
    }
    function reopen() {
        if (busy || filePickerActive) return;
        if (draft && paste.text.trim().length) { practicing = false; return; }
        samplesExpanded = false;
        send({action: "resume"});
    }
    Timer {
        interval: 500
        repeat: true
        running: root.visible && root.practicing && !root.busy
        onTriggered: {
            root.speedNow = Date.now();
            root.speedState = TypingSpeed.tick(root.speedState, root.speedNow, true);
        }
    }
    function saveProgress() {
        if (!dirty || !bookId || busy || restoring) return;
        dirty = false;
        send({action: "save", id: bookId, position: position, typed: answer.text, loops: rounds}, false);
    }
    function openBook(id) {
        if (busy) return;
        saveProgress(); draft = false; resumeOnOpen = true;
        send({action: "open", id: id});
    }
    function seek(offset) {
        if (!bookId || busy) return;
        dirty = false;
        send({action: "seek", id: bookId, position: Math.max(0, Math.min(bookLength - 1, offset)), typed: "", loops: rounds});
    }
    function jumpChapter(index) {
        if (!bookId || busy || index < 0 || index >= chapters.length) return;
        dirty = false;
        send({action: "chapter", id: bookId, index: index, loops: rounds});
    }
    function receive(line) {
        try {
            const data = JSON.parse(line);
            if (data.action === "list") { if (data.books) library = data.books; return; }
            if (data.error) { if (data.request === pageRequest) { busy = false; turningPage = false; } if (data.action === "save") dirty = true; message = data.error; errorMessage = data.error; return; }
            if (data.request !== pageRequest) return;
            if (data.empty) { busy = false; practicing = false; return; }
            if (!data.passage) return;
            // Old versions could save a full, mistyped 90-character window.
            // Rebase that saved input into measured pages without changing the
            // absolute book position or counting restored text toward WPM.
            if (restoreAction && data.action === "next") {
                data.action = restoreAction;
                data.chapters = restoreChapters;
            }
            const fitted = TypingPaging.layout(data.passage, Math.max(80, root.width - 52), characterWidth, pageLineLimit);
            const prepared = TypingPaging.prepareInput(data.typed, fitted.text);
            data.typed = prepared.text;
            const entered = characters(data.typed);
            const pageCount = characters(fitted.text).length;
            if (data.action !== "next" && pageCount > 0 && entered.length >= pageCount && !prepared.pending) {
                restoreAction = data.action;
                restoreChapters = data.chapters || chapters;
                const next = data.position + pageCount;
                send({action: "next", id: data.id, position: next >= data.length ? 0 : next,
                    typed: entered.slice(pageCount).join(""), loops: data.loops + (next >= data.length ? 1 : 0)});
                return;
            }
            restoreAction = ""; restoreChapters = [];
            if (data.action === "next") {
                speedCommitted += Math.max(0, correctCount() - speedBaseline);
                speedBaseline = 0;
                speedState = TypingSpeed.pause(speedState);
            }
            restoring = true;
            bookId = data.id; bookTitle = data.title; bookLength = data.length;
            position = data.position; rounds = data.loops; if (data.chapters) chapters = data.chapters;
            pageSource = data.passage; fitPage();
            answer.text = data.typed; answer.cursorPosition = answer.length;
            dirty = false; draft = false; busy = false; restoring = false;
            turningPage = false;
            if (data.action === "next") {
                if (Motion.enabled && visible && practicing) pageArrival.restart();
                else pageReveal = 1;
                const buffered = pendingKeys; pendingKeys = "";
                if (buffered.length) Qt.callLater(() => {
                    answer.text = buffered; answer.cursorPosition = answer.length;
                    if (!root.visible || !root.practicing) root.saveProgress();
                });
            } else { pendingKeys = ""; pageReveal = 1; }
            message = "Ready to resume. Your place is saved on this device.";
            if (data.kind === "book") samplesExpanded = false;
            if (data.action === "add") { paste.text = ""; practicing = true; }
            if (data.action === "import") { paste.text = ""; practicing = false; }
            if (data.action === "chapter" || data.action === "resume") practicing = true;
            if (data.action === "open" && resumeOnOpen) { resumeOnOpen = false; practicing = true; }
            if (data.action !== "next") resetSpeed();
            if (practicing && visible) Qt.callLater(() => answer.forceActiveFocus());
            if (data.action !== "next") send({action: "list"}, false);
        } catch (error) { busy = false; message = "Could not read the book service response."; }
    }
    Timer { id: saveDelay; interval: 650; onTriggered: root.saveProgress() }
    Timer { interval: 5000; running: root.backendStarted; repeat: true; onTriggered: root.saveProgress() }

    function status() {
        return JSON.stringify({practicing: practicing, fullscreen: fullscreen, pageLines: pageLayout.lines, turningPage: turningPage, textLength: bookLength,
            typed: answer.text.length, position: position, rounds: rounds,
            presets: TypingTexts.passages.length, message: message, busy: busy,
            title: bookTitle, chapters: chapters.length, library: library.length, books: libraryBooks.length, wpm: liveWpm, filePickerActive: filePickerActive});
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
    component ThemeSelect: ComboBox {
        id: select
        implicitHeight: 48
        textRole: "title"
        leftPadding: 12
        rightPadding: 32
        contentItem: StyledText {
            text: select.displayText
            color: select.activeFocus ? Colors.primary : Colors.overSurface
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        indicator: StyledText {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: "⌄"
            color: Colors.primary
        }
        background: StyledRect {
            variant: "pane"
            radius: 12
            backgroundOpacity: 0.35
            border.width: 1
            border.color: select.activeFocus ? Colors.primary : Qt.alpha(Colors.outlineVariant, 0.55)
        }
        delegate: ItemDelegate {
            required property int index
            width: select.width - 12
            implicitHeight: 40
            text: select.textAt(index)
            highlighted: select.highlightedIndex === index
            contentItem: StyledText {
                text: parent.text
                color: parent.highlighted ? Colors.primary : Colors.overSurface
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            background: Rectangle {
                radius: 8
                color: parent.highlighted ? Qt.alpha(Colors.primary, 0.16) : "transparent"
            }
        }
        popup: Popup {
            y: select.height + 4
            width: select.width
            padding: 6
            modal: true
            dim: false
            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
            background: StyledRect { variant: "popup"; radius: 12 }
            contentItem: ListView {
                id: options
                clip: true
                implicitHeight: Math.min(select.count * 40, 260)
                model: select.delegateModel
                currentIndex: select.highlightedIndex
                ScrollBar.vertical: ScrollBar {
                    contentItem: Rectangle { implicitWidth: 4; radius: 2; color: Qt.alpha(Colors.primary, 0.65) }
                    background: Item {}
                }
            }
            onOpened: Qt.callLater(() => options.positionViewAtIndex(Math.max(0, select.currentIndex), ListView.Contain))
        }
    }
    function loadPreset(index) {
        if (busy || index < 0 || index >= TypingTexts.passages.length) return;
        saveProgress();
        paste.text = TypingTexts.passages[index].text;
        draftKind = "practice"; samplesExpanded = true;
        draftTitle = TypingTexts.passages[index].title;
        draft = true; practicing = false;
        message = draftTitle + " loaded. Choose Start practice.";
    }
    function showLibrary() {
        samplesExpanded = false;
        saveProgress();
        send({action: "list"}, false);
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
    Keys.onEscapePressed: event => { root.handleEscape(); event.accepted = true; }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_F11) { root.toggleFullscreen(); event.accepted = true; }
    }
    function start() {
        if (busy) return;
        if (draft || !bookId) {
            if (!paste.text.trim().length) { message = "Add some text or import a book first."; return; }
            send({action: "add", title: draftTitle, text: paste.text, kind: draftKind});
        } else { practicing = true; answer.forceActiveFocus(); }
    }
    function advance() {
        if (restoring || busy || !bookId) return;
        const prepared = TypingPaging.prepareInput(answer.text, passage);
        if (prepared.text !== answer.text) {
            const cursor = answer.cursorPosition;
            const removed = answer.text.length - prepared.text.length;
            answer.text = prepared.text;
            answer.cursorPosition = Math.max(0, cursor - removed);
            return;
        }
        if (characters(answer.text).length > 4096) {
            answer.text = characters(answer.text).slice(0, 4096).join("");
            answer.cursorPosition = answer.length;
            return;
        }
        speedNow = Date.now();
        speedState = TypingSpeed.record(speedState, speedNow);
        dirty = true; saveDelay.restart();
        const pageCount = characters(passage).length;
        const entered = characters(answer.text);
        if (!pageCount || entered.length < pageCount || prepared.pending) return;
        pendingKeys = entered.slice(pageCount).join("") + pendingKeys;
        restoring = true;
        answer.text = entered.slice(0, pageCount).join("");
        answer.cursorPosition = answer.length;
        restoring = false;
        const next = position + pageCount;
        dirty = false; turningPage = true;
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
                TextButton { objectName: "typing-fullscreen"; text: root.fullscreen ? "Exit fullscreen" : "Fullscreen"; onClicked: root.toggleFullscreen() }
                TextButton { objectName: "typing-library"; visible: root.practicing; text: "Library"; onClicked: root.showLibrary() }
                TextButton { visible: root.practicing; text: "Import"; enabled: !root.busy; onClicked: root.openImport() }
                TextButton { objectName: "typing-back"; visible: !root.practicing; text: "Back"; enabled: !root.busy && (root.bookId.length > 0 || root.draft || root.library.length > 0); onClicked: root.goBack() }
                TextButton { text: "Close"; onClicked: { root.saveProgress(); root.backRequested(); } }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12
                StyledText { visible: !root.practicing && (root.errorMessage.length > 0 || !root.bookId); opacity: 0.55; text: root.message; Layout.fillWidth: true; wrapMode: Text.Wrap }
                RowLayout {
                    visible: !root.practicing
                    Layout.maximumHeight: 36
                    TextButton { text: root.busy ? "Loading…" : "Import EPUB / PDF"; objectName: "typing-import"; enabled: !root.busy; onClicked: root.openImport() }
                    TextButton { text: "Paste text"; enabled: !root.busy; onClicked: { root.saveProgress(); root.draft = true; root.draftTitle = "Pasted text"; root.draftKind = "book"; paste.text = ""; paste.forceActiveFocus(); } }
                    TextButton { text: root.bookId && !root.draft ? "Resume" : "Start practice"; enabled: !root.busy; onClicked: root.start() }
                }
                ListView {
                    id: bookCards
                    objectName: "typing-book-cards"
                    visible: !root.practicing && !root.draft && root.libraryBooks.length > 0
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 100
                    clip: true
                    spacing: 8
                    model: root.libraryBooks
                    currentIndex: -1
                    delegate: Button {
                        id: bookCard
                        required property var modelData
                        width: bookCards.width
                        implicitHeight: 86
                        padding: 12
                        enabled: !root.busy
                        Accessible.name: modelData.title + ", " + (modelData.completion * 100).toFixed(1) + "% complete"
                        onClicked: root.openBook(modelData.id)
                        background: StyledRect {
                            variant: "pane"
                            radius: 12
                            backgroundOpacity: bookCard.hovered || bookCard.activeFocus ? 0.65 : 0.35
                            border.width: 1
                            border.color: bookCard.modelData.id === root.bookId || bookCard.activeFocus ? Colors.primary : Qt.alpha(Colors.outlineVariant, 0.4)
                        }
                        contentItem: ColumnLayout {
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                StyledText { text: bookCard.modelData.title; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight; color: Colors.overSurface }
                                StyledText { objectName: "typing-card-progress"; text: (bookCard.modelData.completion * 100).toFixed(1) + "%"; color: Colors.primary }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 3
                                radius: 2
                                color: Qt.alpha(Colors.primary, 0.12)
                                Rectangle { width: parent.width * bookCard.modelData.completion; height: parent.height; radius: 2; color: Colors.primary }
                            }
                            StyledText { text: bookCard.modelData.completion >= 1 ? "Completed · Continue again" : (bookCard.modelData.position > 0 || bookCard.modelData.partial > 0 ? "Continue where you left off" : "Start reading and typing"); opacity: 0.55; font.pixelSize: 11 }
                        }
                    }
                    ScrollBar.vertical: ScrollBar {
                        visible: bookCards.contentHeight > bookCards.height
                        contentItem: Rectangle { implicitWidth: 4; radius: 2; color: Qt.alpha(Colors.primary, 0.6) }
                        background: Item {}
                    }
                }
                StyledText {
                    visible: !root.practicing && !root.draft && !root.libraryBooks.length
                    text: "Your books will appear here. Import an EPUB or PDF to begin."
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    opacity: 0.6
                }
                ColumnLayout {
                    visible: !root.practicing && root.bookId.length > 0 && !root.draft
                    Layout.fillWidth: true
                    StyledText { text: "Jump to chapter"; color: Colors.overSurfaceVariant; font.pixelSize: 12 }
                    RowLayout {
                        Layout.fillWidth: true
                        TextButton { text: "‹"; enabled: !root.busy && root.currentChapterIndex > 0; onClicked: root.jumpChapter(root.currentChapterIndex - 1) }
                        ThemeSelect {
                            id: chapterSelect
                            objectName: "typing-chapter-select"
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            model: root.chapters
                            currentIndex: root.currentChapterIndex
                            enabled: !root.busy
                            displayText: root.chapterTitle
                            onActivated: index => root.jumpChapter(index)
                        }
                        TextButton { text: "›"; enabled: !root.busy && root.currentChapterIndex + 1 < root.chapters.length; onClicked: root.jumpChapter(root.currentChapterIndex + 1) }
                    }
                }
                Slider {
                    id: bookPositionSlider
                    objectName: "typing-book-position"
                    visible: !root.practicing && root.bookId.length > 0 && !root.draft
                    Layout.fillWidth: true
                    implicitHeight: 24
                    background: Rectangle {
                        x: bookPositionSlider.leftPadding
                        y: bookPositionSlider.topPadding + bookPositionSlider.availableHeight / 2 - height / 2
                        width: bookPositionSlider.availableWidth
                        height: 4
                        radius: 2
                        color: Qt.alpha(Colors.primary, 0.14)
                        Rectangle { width: parent.width * bookPositionSlider.visualPosition; height: parent.height; radius: 2; color: Colors.primary }
                    }
                    handle: Rectangle {
                        x: bookPositionSlider.leftPadding + bookPositionSlider.visualPosition * (bookPositionSlider.availableWidth - width)
                        y: bookPositionSlider.topPadding + bookPositionSlider.availableHeight / 2 - height / 2
                        implicitWidth: 14; implicitHeight: 14; radius: 7
                        color: bookPositionSlider.pressed ? Colors.primary : Colors.overSurface
                        border.width: 2; border.color: Colors.primary
                    }
                    from: 0; to: Math.max(1, root.bookLength - 1)
                    value: root.position
                    onMoved: jumpDelay.restart()
                    Timer { id: jumpDelay; interval: 250; onTriggered: root.seek(Math.round(bookPositionSlider.value)) }
                    ToolTip.visible: hovered || pressed
                    ToolTip.text: "Book position · " + (100 * value / Math.max(1, root.bookLength)).toFixed(1) + "%"
                }
                TextButton {
                    objectName: "typing-samples-toggle"
                    visible: !root.practicing
                    text: root.samplesExpanded ? "Practice samples ▴" : "Practice samples ▾"
                    onClicked: root.samplesExpanded = !root.samplesExpanded
                }
                RowLayout {
                    visible: !root.practicing && root.samplesExpanded
                    Layout.fillWidth: true
                    StyledText { text: "Optional samples"; opacity: 0.5 }
                    ThemeSelect {
                        id: presets
                        Layout.fillWidth: true
                        model: TypingTexts.passages
                        textRole: "title"
                        currentIndex: -1
                        displayText: currentIndex < 0 ? "Choose a built-in passage…" : currentText
                        onActivated: index => root.loadPreset(index)
                    }
                }
                StyledText {
                    visible: !root.practicing && root.samplesExpanded
                    text: "Original passages · CC0 · Free to copy, change and share"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                ScrollView {
                    background: Item {}
                    visible: !root.practicing && root.draft && !presets.popup.visible
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    TextArea {
                        id: paste
                        placeholderText: "Paste a book or text here, or import EPUB / PDF…"
                        onTextChanged: { if (activeFocus && !root.restoring) { root.draft = true; root.draftTitle = "Pasted text"; root.draftKind = "book"; } }
                        background: Item {}
                        placeholderTextColor: Qt.alpha(Colors.overSurface, 0.35)
                        wrapMode: TextEdit.Wrap
                        color: Colors.overSurface
                        font.family: Config.theme.font
                        font.pixelSize: 14
                    }
                }
                ColumnLayout {
                    visible: root.practicing
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Item {
                        id: passageArea
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        onWidthChanged: {
                            if (root.pageSource.length && !answer.text.length) fitDelay.restart();
                            Qt.callLater(() => { if (smoothCaret.targetGlyph) smoothCaret.follow(smoothCaret.targetGlyph); });
                        }
                        Flow {
                            opacity: root.pageReveal
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.leftMargin: 6
                            anchors.rightMargin: 6
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
                                            property bool caretHere: false
                                            property bool typed: false
                                            property bool incorrect: false
                                            property bool initialized: false
                                            property real lift: 0
                                            property real zoom: 1
                                            property real shine: 0
                                            property real entrance: 1
                                            scale: zoom
                                            transform: Translate { y: glyph.lift + (1 - glyph.entrance) * 7 }
                                            onCaretHereChanged: { if (caretHere && initialized) Qt.callLater(() => smoothCaret.follow(glyph)); }
                                            Connections {
                                                target: word
                                                function onXChanged() { if (glyph.caretHere) Qt.callLater(() => smoothCaret.follow(glyph)); }
                                                function onYChanged() { if (glyph.caretHere) Qt.callLater(() => smoothCaret.follow(glyph)); }
                                            }
                                            onTypedChanged: {
                                                if (!initialized) return;
                                                if (typed && Motion.enabled && visible) letterPop.restart();
                                                else { letterPop.stop(); lift = 0; zoom = 1; shine = 0; }
                                            }
                                            Component.onCompleted: {
                                                root.glyphItems[characterIndex] = glyph;
                                                root.updateGlyph(glyph);
                                                initialized = true;
                                                if (Motion.enabled && visible && !root.fullscreen) entranceAnimation.start();
                                                if (caretHere) Qt.callLater(() => smoothCaret.follow(glyph));
                                            }
                                            Component.onDestruction: {
                                                if (root.glyphItems[characterIndex] === glyph) delete root.glyphItems[characterIndex];
                                            }
                                            onVisibleChanged: { if (initialized && visible) { if (Motion.enabled && !root.fullscreen) entranceAnimation.restart(); if (caretHere) Qt.callLater(() => smoothCaret.follow(glyph)); } }
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
                                            width: root.characterWidth(modelData)
                                            font.family: Config.theme.font
                                            font.pixelSize: 22
                                            font.underline: false
                                            lineHeight: 1.45
                                            property real inkOpacity: 1
                                            opacity: caretHere ? 1 : inkOpacity * entrance
                                            Behavior on inkOpacity {
                                                enabled: Motion.enabled
                                                NumberAnimation { duration: Math.round(Motion.base * 0.45); easing.type: Easing.OutCubic }
                                            }
                                            color: caretHere ? root.readingAccent : (typed ? (incorrect ? root.readingError : Qt.tint(root.readingInk, Qt.alpha(root.readingAccent, shine * 0.65))) : root.readingUpcoming)
                                            style: Text.Outline
                                            styleColor: root.outlineFor(color)
                                            Rectangle {
                                                objectName: "typing-caret-" + glyph.characterIndex
                                                x: -1
                                                y: Math.max(0, glyph.baselineOffset - glyph.font.pixelSize - 1)
                                                width: parent.width + 2
                                                height: glyph.font.pixelSize + 6
                                                z: -1
                                                radius: 4
                                                color: Qt.alpha(root.readingAccent, 0.10)
                                                visible: glyph.caretHere
                                            }

                                        }
                                    }
                                }
                            }
                        }
                        Item {
                            id: smoothCaret
                            objectName: "typing-smooth-caret"
                            property Item targetGlyph: null
                            property bool glide: false
                            property real breath: 1
                            property bool placed: false
                            width: 2.5
                            height: 26
                            z: 2
                            visible: root.practicing && root.passage.length > 0 && !root.busy && placed && targetGlyph !== null && targetGlyph.caretHere
                            function follow(item) {
                                if (!item || !item.caretHere || !item.visible) return;
                                const point = item.parent.mapToItem(passageArea, item.x, item.y);
                                const nextY = point.y + Math.max(0, item.baselineOffset - item.font.pixelSize);
                                glide = placed && Math.abs(nextY - y) < 2 && Motion.enabled;
                                targetGlyph = item;
                                x = Math.max(1, point.x - 3);
                                y = nextY;
                                height = Math.round(item.font.pixelSize * 1.15);
                                placed = true;
                                if (Motion.enabled) idlePulse.restart();
                            }
                            Behavior on x {
                                enabled: smoothCaret.glide
                                NumberAnimation { duration: Math.min(110, Motion.feedback); easing.type: Easing.OutCubic }
                            }
                            SequentialAnimation {
                                id: idlePulse
                                running: smoothCaret.visible && Motion.enabled
                                loops: Animation.Infinite
                                NumberAnimation { target: smoothCaret; property: "breath"; from: 1; to: 0.65; duration: 700; easing.type: Easing.InOutSine }
                                NumberAnimation { target: smoothCaret; property: "breath"; from: 0.65; to: 1; duration: 700; easing.type: Easing.InOutSine }
                            }
                            Rectangle {
                                anchors.centerIn: parent
                                width: 9
                                height: parent.height + 4
                                radius: 4
                                color: Qt.alpha(Colors.primary, 0.10)
                            }
                            Rectangle {
                                objectName: "typing-caret-core"
                                anchors.fill: parent
                                radius: width / 2
                                color: root.readingAccent
                                border.width: 1
                                border.color: root.outlineFor(color)
                                opacity: Motion.enabled ? smoothCaret.breath : 1
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
                            selectByMouse: false
                            font.family: Config.theme.font
                            font.pixelSize: 22
                            TapHandler { onTapped: { answer.forceActiveFocus(); answer.cursorPosition = answer.length; } }
                            wrapMode: TextEdit.Wrap
                            inputMethodHints: Qt.ImhNoPredictiveText
                            readOnly: root.busy
                            onTextChanged: { root.advance(); root.syncGlyphs(); }
                            onCursorPositionChanged: root.syncCaret()
                            Keys.onPressed: event => {
                                if (event.key === Qt.Key_F11) { root.toggleFullscreen(); event.accepted = true; return; }
                                if (!root.turningPage || (event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier))) return;
                                if (event.key === Qt.Key_Backspace) { root.undoQueuedKey(); event.accepted = true; }
                                else if (event.text.length && event.text.charCodeAt(0) >= 32) { root.queueTyping(event.text); event.accepted = true; }
                            }
                            Keys.onEscapePressed: event => { root.handleEscape(); event.accepted = true; }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: root.errorMessage || root.chapterTitle; opacity: 0.5; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true; Layout.minimumWidth: 0 }
                        StyledText { objectName: "typing-live-wpm"; text: root.liveWpm + " WPM"; color: Colors.primary; font.pixelSize: 12 }
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
