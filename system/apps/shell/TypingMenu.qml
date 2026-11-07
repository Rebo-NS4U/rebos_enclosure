pragma ComponentBehavior: Bound
import QtQuick
import "TypingTexts.js" as TypingTexts
import "TypingSpeed.js" as TypingSpeed
import "TypingPaging.js" as TypingPaging
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
    readonly property real passageLineHeight: Math.ceil(typingMetrics.height * 1.45)
    readonly property int pageLineLimit: Math.max(1, Math.floor(Math.max(0, passageArea.height - 8) / Math.max(1, passageLineHeight)))
    onPageLineLimitChanged: fitDelay.restart()
    onReadingFontChanged: fitDelay.restart()
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
    property var pageLayout: ({text: "", words: [], lines: 0, lineWidths: []})
    readonly property string passage: pageLayout.text
    property bool turningPage: false
    property var pageHistory: []
    property bool historyBack: false
    property bool backAfterTurn: false
    property int pageDirection: 1
    property string pendingKeys: ""
    property string restoreAction: ""
    property var restoreChapters: []
    property int feedbackEvents: 0
    property int lineTransitions: 0
    property int pageTransitions: 0
    property var chapters: []
    property var library: []
    property bool backendStarted: false
    property bool ready: false
    property bool busy: false
    property bool dirty: false
    property bool restoring: false
    property bool editingCorrection: false
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
    readonly property string displayedInput: TypingPaging.displayInput(answer.text, passage)
    onDisplayedInputChanged: syncGlyphs()
    onVisualCursorChanged: syncCaret()
    readonly property int visualCursor: Math.min(TypingPaging.displayInput(answer.text.slice(0, answer.cursorPosition), passage).length, passage.length - 1)
    readonly property real progress: bookLength ? Math.min(1, (position + characters(displayedInput).length) / bookLength) : 0
    readonly property var passageWords: pageLayout.words
    readonly property font readingFont: Qt.font({family: Config.theme.font, pixelSize: Config.theme.fontSize + 2, weight: Font.Normal})
    FontMetrics { id: typingMetrics; font: root.readingFont }
    readonly property rect highlightBounds: {
        const metricsFont = typingMetrics.font;
        return typingMetrics.tightBoundingRect("Hg");
    }
    readonly property real highlightPadding: 3
    readonly property real letterPadding: 1
    function characterWidth(text) { return Math.max(1, Math.ceil(typingMetrics.advanceWidth(text))); }
    function fitPage() {
        stopFeedback();
        pageLayout = TypingPaging.layout(pageSource, Math.max(80, root.width - 40), characterWidth, pageLineLimit);
        Qt.callLater(refreshPageCaret);
    }
    function refreshPageCaret() {
        if (busy || restoring) return;
        passageFlow.forceLayout();
        syncCaret();
        const current = glyphItems[renderedCaret];
        updateGlyph(current);
        smoothCaret.follow(current);
    }
    function resetPageCaret() {
        stopFeedback();
        smoothCaret.placed = false;
        smoothCaret.targetGlyph = null;
        renderedCaret = -1;
    }
    Timer {
        id: fitDelay
        interval: 150
        onTriggered: { if (root.visible && root.practicing && passageArea.width > 0 && passageArea.height > 0 && !root.restoring && root.pageSource.length) { root.fitPage(); if (root.bookId && root.characters(answer.text).length >= root.characters(root.passage).length) root.advance(); } }
    }
    property string effectKind: ""
    property int effectLine: -1
    property real effectStrength: 0
    property var glowingGlyphs: []
    onEffectStrengthChanged: {
        if (effectKind === "line") Qt.callLater(refreshPageCaret);
    }
    readonly property int activeEffects: (feedbackAnimation.running ? 1 : 0) + glowingGlyphs.length
    function forgetGlyph(glyph) {
        glowingGlyphs = glowingGlyphs.filter(item => item !== glyph);
    }
    function stopLetters() {
        const previous = glowingGlyphs;
        glowingGlyphs = [];
        for (const glyph of previous) glyph.stopFeedback();
    }
    function stopFeedback() {
        feedbackAnimation.stop(); stopLetters(); effectStrength = 0; effectKind = ""; effectLine = -1;
    }
    function requestFeedback(kind, glyph = null) {
        if (!Motion.enabled || !visible || !practicing) return;
        if (kind === "letter") {
            if (!glyph) return;
            // Each keystroke finishes its own fade, even during the next key or row.
            glyph.stopFeedback();
            if (glowingGlyphs.length >= 12) glowingGlyphs[0].stopFeedback();
            glowingGlyphs = glowingGlyphs.concat([glyph]);
            feedbackEvents++;
            glyph.startFeedback();
            return;
        }
        if (feedbackAnimation.running && effectKind === "page" && kind === "line") return;
        feedbackAnimation.stop();
        if (kind === "page") stopLetters();
        effectStrength = 0;
        effectKind = kind;
        effectLine = kind === "line" && glyph ? glyph.parent.modelData.line : -1;
        if (kind === "line") lineTransitions++;
        else pageTransitions++;
        feedbackAnimation.restart();
    }
    NumberAnimation {
        id: feedbackAnimation
        target: root
        property: "effectStrength"
        from: 1
        to: 0
        duration: effectKind === "page" ? Math.max(720, Motion.enter * 2.2) : Math.max(520, Motion.enter * 1.6)
        easing.type: Easing.OutCubic
        onFinished: { root.effectStrength = 0; root.effectKind = ""; root.effectLine = -1; }
    }
    component PopHalo: Rectangle {
        property real strength: 0
        property real growth: 0.12
        radius: 5
        color: Qt.alpha(Colors.primary, 0.07)
        border.width: 1
        border.color: Qt.alpha(Colors.primary, 0.22)
        scale: 1 + (1 - strength) * growth
        opacity: strength
        visible: opacity > 0
    }
    Connections {
        target: Motion
        function onEnabledChanged() { if (!Motion.enabled) root.stopFeedback(); }
    }
    function queueTyping(text) {
        if (turningPage) pendingKeys = characters(pendingKeys + text).slice(0, 4096).join("");
    }
    function undoQueuedKey() {
        if (turningPage) pendingKeys = characters(pendingKeys).slice(0, -1).join("");
    }
    implicitHeight: practicing ? 116 + 4 * passageLineHeight : 600
    onPracticingChanged: { resetSpeed(); syncCaret(); }
    onVisibleChanged: {
        if (visible) { backendStarted = true; if (ready) send({action: "list"}, false); }
        else { saveProgress(); stopFeedback(); }
        resetSpeed();
        if (visible && practicing) { fitDelay.restart(); Qt.callLater(() => answer.forceActiveFocus()); }
    }
    Component.onCompleted: { if (visible) backendStarted = true; }
    function send(data, page = true) {
        data.window = 4096;
        data.request = ++requestId;
        if (page) { pageRequest = data.request; busy = true; errorMessage = ""; }
        if (ready) backend.write(JSON.stringify(data) + "\n");
        else { queued = queued.concat([data]); backendStarted = true; }
    }
    // Keep input dependencies off the thousands of static glyph delegates.
    property var glyphItems: ({})
    property string renderedInput: ""
    property int renderedCaret: -1
    function updateGlyph(glyph) {
        if (!glyph) return;
        const wasCorrect = glyph.typed && !glyph.incorrect;
        glyph.typed = glyph.characterIndex < displayedInput.length;
        glyph.incorrect = glyph.typed && !TypingPaging.matchingCharacter(displayedInput.substr(glyph.characterIndex, glyph.modelData.length), glyph.modelData);
        glyph.caretHere = practicing && glyph.characterIndex === visualCursor;
        if (!glyph.typed || glyph.incorrect) glyph.stopFeedback();
        else if (!wasCorrect && glyph.initialized && !restoring && !busy && visible && practicing && answer.activeFocus && Motion.enabled && glyph.modelData.trim().length)
            glyph.celebrate();
    }
    function syncCaret() {
        const previous = renderedCaret;
        renderedCaret = practicing ? visualCursor : -1;
        if (previous !== renderedCaret) {
            updateGlyph(glyphItems[previous]);
            updateGlyph(glyphItems[renderedCaret]);
        }
    }
    function syncGlyphs() {
        const current = displayedInput;
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
        const input = characters(displayedInput);
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
        running: root.visible && root.practicing && !root.busy && answer.activeFocus
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
    function previousPage() {
        if (busy || !bookId || answer.text.length || (!position && !rounds)) return;
        saveDelay.stop();
        dirty = false; turningPage = true; pageDirection = -1;
        const previous = pageHistory.length ? pageHistory[pageHistory.length - 1] : null;
        historyBack = !!previous && previous.width === width && previous.lines === pageLineLimit;
        if (historyBack) send({action: "previous", id: bookId, resolved: true, position: previous.position,
            typed: characters(previous.typed).slice(0, -1).join(""), loops: previous.rounds});
        else send({action: "previous", id: bookId, position: position, loops: rounds});
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
            if (data.error) { if (data.request === pageRequest) { busy = false; turningPage = false; historyBack = false; backAfterTurn = false; } if (data.action === "save") dirty = true; message = data.error; errorMessage = data.error; return; }
            if (data.request !== pageRequest) return;
            if (data.atBeginning) { busy = false; turningPage = false; return; }
            if (data.previousText !== undefined) {
                let offset = 0, last = 0, text = "";
                while (offset < data.previousText.length) {
                    last = offset;
                    text = TypingPaging.layout(data.previousText.slice(offset), Math.max(80, width - 40), characterWidth, pageLineLimit).text;
                    if (!text.length) break;
                    offset += text.length;
                }
                send({action: "previous", id: bookId, resolved: true,
                    position: data.previousStart + characters(data.previousText.slice(0, last)).length,
                    typed: characters(text).slice(0, -1).join(""), loops: data.loops});
                return;
            }
            if (data.empty) { busy = false; practicing = false; return; }
            if (!data.passage) return;
            // Old versions could save a full, mistyped 90-character window.
            // Rebase that saved input into measured pages without changing the
            // absolute book position or counting restored text toward WPM.
            if (restoreAction && data.action === "next") {
                data.action = restoreAction;
                data.chapters = restoreChapters;
            }
            const fitted = TypingPaging.layout(data.passage, Math.max(80, root.width - 40), characterWidth, pageLineLimit);
            const prepared = TypingPaging.prepareInput(data.typed, fitted.text);
            data.typed = prepared.text;
            const entered = characters(data.typed);
            const pageCount = characters(fitted.text).length;
            if (data.action !== "next" && data.action !== "previous" && pageCount > 0 && entered.length >= pageCount && !prepared.pending) {
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
            if (bookId !== data.id || ["seek", "chapter", "open", "add", "import"].indexOf(data.action) >= 0) pageHistory = [];
            if (data.action === "previous") {
                pageHistory = historyBack ? pageHistory.slice(0, -1) : [];
                historyBack = false;
            }
            restoring = true;
            bookId = data.id; bookTitle = data.title; bookLength = data.length;
            position = data.position; rounds = data.loops; if (data.chapters) chapters = data.chapters;
            resetPageCaret();
            pageSource = data.passage; fitPage();
            answer.text = data.typed; answer.cursorPosition = answer.length;
            dirty = false; draft = false; busy = false; restoring = false;
            turningPage = false;
            if (data.action === "next" || data.action === "previous") {
                if (Motion.enabled && visible && practicing) requestFeedback("page");
                const buffered = pendingKeys; pendingKeys = "";
                if (buffered.length) Qt.callLater(() => {
                    answer.text = data.action === "previous" ? answer.text + buffered : buffered; answer.cursorPosition = answer.length;
                    if (!root.visible || !root.practicing) root.saveProgress();
                });
            } else { pendingKeys = ""; stopFeedback(); }
            if (backAfterTurn && data.action === "next") { backAfterTurn = false; Qt.callLater(previousPage); }
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
        return JSON.stringify({practicing: practicing, fullscreen: fullscreen, pageLines: pageLayout.lines, pageLineLimit: pageLineLimit, passageHeight: passageArea.height, renderedHeight: passageFlow.height, fontSize: readingFont.pixelSize, layoutVersion: 9, previousPages: pageHistory.length, activeEffects: activeEffects, effectKind: effectKind, lineTransitions: lineTransitions, pageTransitions: pageTransitions, motionEnabled: Motion.enabled, feedbackEvents: feedbackEvents, focused: answer.activeFocus, turningPage: turningPage, textLength: bookLength,
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
            opacity: !parent.enabled ? 0.3 : (parent.down || parent.activeFocus ? 1 : (parent.hovered ? 0.9 : 0.75))
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.underline: parent.activeFocus

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
        start();
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
    function normalizeInput() {
        if (restoring || busy || !bookId) return;
        const prepared = TypingPaging.prepareInput(answer.text, passage);
        if (prepared.text === answer.text) return;
        const prefix = TypingPaging.prepareInput(answer.text.slice(0, answer.cursorPosition), passage);
        restoring = true;
        // Edit the native document rather than resetting it, which moves Qt's
        // insertion point to the end when composing inside an existing line.
        const previous = answer.text;
        let first = 0;
        while (first < prepared.text.length && previous[first] === prepared.text[first]) first++;
        let end = previous.length, replacementEnd = prepared.text.length;
        while (end > first && replacementEnd > first && previous[end - 1] === prepared.text[replacementEnd - 1]) { end--; replacementEnd--; }
        answer.remove(first, end);
        answer.insert(first, prepared.text.slice(first, replacementEnd));
        answer.cursorPosition = prefix.text.length;
        restoring = false;
        editingCorrection = answer.cursorPosition < answer.length;
        if (answer.cursorPosition === answer.length) advance();
        else { dirty = true; saveDelay.restart(); }
        syncGlyphs();
    }
    function advance() {
        if (restoring || busy || !bookId) return;
        const prepared = TypingPaging.prepareInput(answer.text, passage);
        if (prepared.text !== answer.text) {
            // Let Qt finish the key edit before replacing its document/cursor.
            Qt.callLater(normalizeInput);
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
        if (!answer.text.length || answer.cursorPosition === answer.length) editingCorrection = false;
        const pageCount = characters(passage).length;
        const entered = characters(answer.text);
        if (!pageCount || entered.length < pageCount || prepared.pending || editingCorrection) return;
        pageHistory = pageHistory.concat([{position: position, rounds: rounds, typed: entered.slice(0, pageCount).join(""), width: width, lines: pageLineLimit}]).slice(-128);
        pendingKeys = entered.slice(pageCount).join("") + pendingKeys;
        restoring = true;
        answer.text = entered.slice(0, pageCount).join("");
        answer.cursorPosition = answer.length;
        restoring = false;
        const next = position + pageCount;
        dirty = false; turningPage = true; pageDirection = 1;
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
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.practicing ? 12 : 20
            anchors.leftMargin: root.practicing ? 16 : 20
            anchors.rightMargin: root.practicing ? 16 : 20
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Layout.maximumHeight: 36
                StyledText { text: root.practicing ? root.bookTitle : "Your book library"; textFormat: Text.PlainText; elide: Text.ElideRight; Layout.minimumWidth: 0; font.pixelSize: 18; opacity: 0.65; Layout.fillWidth: true }
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
                StyledText { visible: !root.practicing && (root.errorMessage.length > 0 || !root.bookId); opacity: root.errorMessage ? 1 : 0.7; color: root.errorMessage ? Colors.error : Colors.overSurface; textFormat: Text.PlainText; text: root.message; Layout.fillWidth: true; wrapMode: Text.Wrap }
                RowLayout {
                    visible: !root.practicing
                    Layout.maximumHeight: 36
                    TextButton { text: root.busy ? "Loading…" : "Import EPUB / PDF"; objectName: "typing-import"; enabled: !root.busy; onClicked: root.openImport() }
                    TextButton { text: "Paste text"; enabled: !root.busy; onClicked: { root.saveProgress(); root.draft = true; root.draftTitle = "Pasted text"; root.draftKind = "book"; paste.text = ""; paste.forceActiveFocus(); } }
                    TextButton { text: root.bookId && !root.draft ? "Resume" : "Start practice"; enabled: !root.busy && (root.draft ? paste.text.trim().length > 0 : root.bookId.length > 0); onClicked: root.start() }
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
                                StyledText { text: bookCard.modelData.title; textFormat: Text.PlainText; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight; color: Colors.overSurface }
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
                        objectName: "typing-sample-select"
                        enabled: !root.busy
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
                        textFormat: TextEdit.PlainText
                        Accessible.name: "Text to practice"
                        placeholderText: "Paste a book or text here, or import EPUB / PDF…"
                        onTextChanged: { if (activeFocus && !root.restoring) { root.draft = true; root.draftTitle = "Pasted text"; root.draftKind = "book"; } }
                        background: Item {}
                        placeholderTextColor: Qt.alpha(Colors.overSurface, 0.35)
                        wrapMode: TextEdit.Wrap
                        color: Colors.overSurface
                        font: root.readingFont
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
                            if (root.pageSource.length) fitDelay.restart();
                            Qt.callLater(() => { if (smoothCaret.targetGlyph) smoothCaret.follow(smoothCaret.targetGlyph); });
                        }
                        Item {
                            id: passageVisuals
                            anchors.fill: parent
                            readonly property real pagePop: root.effectKind === "page" ? root.effectStrength : 0
                            objectName: "typing-page-visuals"
                            opacity: 1 - pagePop * 0.10
                            transform: Scale {
                                origin.x: passageVisuals.width / 2
                                origin.y: passageVisuals.height / 2
                                xScale: 1
                                yScale: 1 - passageVisuals.pagePop * 0.012
                            }
                            Rectangle {
                                objectName: "typing-line-highlight"
                                z: -1
                                anchors.left: parent.left
                                anchors.right: parent.right
                                y: smoothCaret.rowY
                                height: smoothCaret.rowHeight
                                radius: 7
                                color: Qt.alpha(Colors.primary, 0.14)
                                border.width: 0
                                visible: smoothCaret.visible
                                opacity: answer.activeFocus ? 1 : 0.4
                            }
                            PopHalo {
                                objectName: "typing-page-celebration"
                                anchors.fill: parent
                                anchors.margins: 6
                                radius: 10
                                growth: 0.015
                                strength: root.effectKind === "page" ? root.effectStrength : 0
                            }
                            PopHalo {
                                objectName: "typing-line-ripple"
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: parent.width - 12
                                height: smoothCaret.rowHeight + 6
                                y: smoothCaret.rowY - 3
                                radius: 7
                                growth: 0.025
                                strength: root.effectKind === "line" ? root.effectStrength : 0
                            }
                            // A quiet sweep shares the feedback clock and respects reduced motion.
                            Item {
                                id: transitionBurst
                                objectName: "typing-transition-burst"
                                anchors.fill: parent
                                z: 3
                                readonly property bool page: root.effectKind === "page"
                                readonly property real strength: root.effectKind === "line" || page ? root.effectStrength : 0
                                readonly property real progress: 1 - Math.pow(strength, 1 / 3)
                                visible: strength > 0
                                Rectangle {
                                    objectName: "typing-line-sweep"
                                    visible: !transitionBurst.page
                                    x: (parent.width + width) * transitionBurst.progress - width
                                    y: smoothCaret.rowY
                                    width: Math.max(60, parent.width * 0.22)
                                    height: smoothCaret.rowHeight
                                    radius: height / 2
                                    opacity: Math.sin(transitionBurst.progress * Math.PI) * 0.12
                                    gradient: Gradient {
                                        orientation: Gradient.Horizontal
                                        GradientStop { position: 0; color: "transparent" }
                                        GradientStop { position: 0.65; color: Colors.primary }
                                        GradientStop { position: 1; color: "transparent" }
                                    }
                                }
                            }
                            Flow {
                                id: passageFlow
                                objectName: "typing-passage-flow"
                                y: 4
                                onYChanged: Qt.callLater(() => { if (smoothCaret.targetGlyph) smoothCaret.follow(smoothCaret.targetGlyph); })
                                z: 1
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.leftMargin: 4
                                anchors.rightMargin: 4
                                spacing: 0
                                Repeater {
                                    model: root.passageWords
                                    delegate: Row {
                                        id: word
                                        required property var modelData
                                        readonly property real linePop: root.effectKind === "line" && root.effectLine === modelData.line ? root.effectStrength : 0
                                        readonly property real centerOffset: Math.max(0, (passageFlow.width - (root.pageLayout.lineWidths[modelData.line] || 0)) / 2)
                                        readonly property real arrival: root.effectKind === "page" ? Math.max(0, 1 - transitionBurst.progress / (0.48 + 0.45 * (modelData.line + 1) / Math.max(1, root.pageLayout.lines))) : 0
                                        readonly property real wave: linePop > 0 ? Math.sin(Math.max(0, Math.min(1, transitionBurst.progress * 1.6 - x / Math.max(1, passageFlow.width) * 0.5)) * Math.PI * 2) * linePop : 0
                                        transform: [
                                            Translate {
                                                x: word.centerOffset + root.pageDirection * word.arrival * 8
                                                y: -1.5 * word.wave + word.arrival * 5
                                            },
                                            Scale {
                                                origin.x: passageFlow.width / 2 - word.x - word.centerOffset
                                                origin.y: word.height / 2
                                                xScale: 1
                                                yScale: 1 + word.linePop * 0.008
                                            }
                                        ]
                                        onArrivalChanged: { if (smoothCaret.targetGlyph?.parent === word) Qt.callLater(root.refreshPageCaret); }
                                        onWaveChanged: { if (smoothCaret.targetGlyph?.parent === word) Qt.callLater(root.refreshPageCaret); }
                                        onCenterOffsetChanged: { if (smoothCaret.targetGlyph?.parent === word) Qt.callLater(() => { if (smoothCaret.targetGlyph) smoothCaret.follow(smoothCaret.targetGlyph); }); }
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
                                                property real spark: 0
                                                scale: 1 + spark * 0.105
                                                transform: Translate { y: -2.2 * glyph.spark }
                                                transformOrigin: Item.Center
                                                function celebrate() { root.requestFeedback("letter", glyph); }
                                                function startFeedback() { keyFeedback.restart(); }
                                                function stopFeedback() { keyFeedback.stop(); spark = 0; root.forgetGlyph(glyph); }
                                                NumberAnimation {
                                                    id: keyFeedback
                                                    target: glyph
                                                    property: "spark"
                                                    from: 1
                                                    to: 0
                                                    duration: Math.max(280, Math.min(420, Motion.feedback * 2.4))
                                                    easing.type: Easing.OutCubic
                                                    onFinished: root.forgetGlyph(glyph)
                                                }
                                                PopHalo {
                                                    objectName: "typing-key-halo-" + glyph.characterIndex
                                                    anchors.centerIn: parent
                                                    width: parent.width + 6
                                                    height: root.highlightBounds.height + 6
                                                    z: -1
                                                    strength: Math.min(1, glyph.spark * 1.4)
                                                }
                                                onCaretHereChanged: { if (caretHere && initialized) Qt.callLater(() => smoothCaret.follow(glyph)); }
                                                Connections {
                                                    target: word
                                                    function onXChanged() { if (glyph.caretHere) Qt.callLater(() => smoothCaret.follow(glyph)); }
                                                    function onYChanged() { if (glyph.caretHere) Qt.callLater(() => smoothCaret.follow(glyph)); }
                                                }
                                                Component.onCompleted: {
                                                    root.glyphItems[characterIndex] = glyph;
                                                    root.updateGlyph(glyph);
                                                    initialized = true;
                                                    if (caretHere) Qt.callLater(() => smoothCaret.follow(glyph));
                                                }
                                                Component.onDestruction: {
                                                    stopFeedback();
                                                    if (root.glyphItems[characterIndex] === glyph) delete root.glyphItems[characterIndex];
                                                }
                                                onVisibleChanged: { if (!visible) stopFeedback(); else if (initialized && caretHere) Qt.callLater(() => smoothCaret.follow(glyph)); }
                                                readonly property int characterIndex: word.modelData.start + root.characters(word.modelData.text).slice(0, index).join("").length
                                                objectName: "typing-character-" + characterIndex
                                                text: modelData === " " ? "\u00a0" : modelData
                                                textFormat: Text.PlainText
                                                width: root.characterWidth(modelData)
                                                font: Qt.font({family: root.readingFont.family, pixelSize: root.readingFont.pixelSize, weight: Font.Normal, underline: glyph.incorrect})
                                                height: root.passageLineHeight
                                                lineHeight: 1.45
                                                property real inkOpacity: caretHere || typed ? 1 : 0.65
                                                Behavior on inkOpacity {
                                                    enabled: Motion.enabled && glyph.initialized && !root.restoring && !root.busy
                                                    NumberAnimation { duration: 110; easing.type: Easing.OutCubic }
                                                }
                                                Behavior on color {
                                                    enabled: Motion.enabled && glyph.initialized && !root.restoring && !root.busy && !glyph.incorrect
                                                    ColorAnimation { duration: 130; easing.type: Easing.OutCubic }
                                                }
                                                opacity: caretHere ? 1 : inkOpacity

                                                color: typed && incorrect ? Colors.error : Qt.tint(Colors.overSurface, Qt.alpha(Colors.primary, Math.min(0.88, (typed ? 0.38 : 0) + spark * 0.50 + (word?.linePop ?? 0) * 0.12)))

                                            }
                                        }
                                    }
                                }
                            }
                            Item {
                                id: smoothCaret
                                objectName: "typing-smooth-caret"
                                opacity: answer.activeFocus ? 1 : 0.45
                                property Item targetGlyph: null
                                property bool placed: false
                                property bool glideAllowed: false
                                Behavior on x {
                                    enabled: Motion.enabled && smoothCaret.placed && smoothCaret.glideAllowed && !root.busy && !root.restoring
                                    NumberAnimation { duration: 100; easing.type: Easing.OutCubic }
                                }
                                property real rowY: 0
                                property real rowHeight: 32
                                readonly property color accent: Colors.primary
                                property real targetRowY: 0
                                property real targetX: 0
                                property real targetY: 0
                                width: 18
                                height: 28
                                z: 0
                                visible: root.practicing && root.passage.length > 0 && !root.busy && placed && targetGlyph !== null && targetGlyph.caretHere
                                function follow(item) {
                                    if (root.busy || root.restoring || !item || !item.caretHere || !item.visible) return;
                                    if (root.glyphItems[item.characterIndex] !== item || item.characterIndex !== root.renderedCaret) return;
                                    const point = item.parent.mapToItem(passageVisuals, item.x, item.y);
                                    const nextY = point.y + item.baselineOffset + root.highlightBounds.y - root.highlightPadding;
                                    const newLine = placed && targetGlyph !== null && item.characterIndex > targetGlyph.characterIndex && nextY > targetRowY + 1;
                                    if (newLine && root.visible && answer.activeFocus && Motion.enabled) root.requestFeedback("line", item);
                                    // Glide through nearby letters; snap across rows and restored pages.
                                    glideAllowed = placed && targetGlyph !== null && Math.abs(nextY - targetRowY) < 1
                                        && Math.abs(item.characterIndex - targetGlyph.characterIndex) <= 2;
                                    targetGlyph = item;
                                    targetRowY = Math.max(0, nextY);
                                    rowY = targetRowY;
                                    rowHeight = root.highlightBounds.height + 2 * root.highlightPadding;
                                    targetX = Math.max(0, point.x - root.letterPadding);
                                    targetY = Math.max(0, nextY + root.highlightPadding - root.letterPadding);
                                    x = targetX;
                                    y = targetY;
                                    width = item.width + 2 * root.letterPadding;
                                    height = root.highlightBounds.height + 2 * root.letterPadding;
                                    placed = true;
                                }
                                Rectangle {
                                    objectName: "typing-caret-core"
                                    anchors.fill: parent
                                    radius: Math.min(4, width / 3, height / 3)
                                    color: Qt.alpha(smoothCaret.accent, 0.46)
                                    border.width: 1
                                    border.color: Qt.alpha(smoothCaret.accent, 0.8)
                                    gradient: Gradient {
                                        GradientStop { position: 0; color: Qt.alpha(smoothCaret.accent, 0.58) }
                                        GradientStop { position: 0.45; color: Qt.alpha(smoothCaret.accent, 0.36) }
                                        GradientStop { position: 1; color: Qt.alpha(smoothCaret.accent, 0.5) }
                                    }
                                    opacity: 1
                                    StyledText {
                                        objectName: "typing-space-indicator"
                                        anchors.centerIn: parent
                                        text: "·"
                                        font.pixelSize: root.readingFont.pixelSize
                                        color: Colors.overSurface
                                        opacity: 0.8
                                        visible: smoothCaret.targetGlyph !== null && smoothCaret.targetGlyph.modelData === " "
                                    }
                                    Rectangle {
                                        anchors.top: parent.top
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.topMargin: 2
                                        anchors.leftMargin: Math.min(3, parent.width / 4)
                                        anchors.rightMargin: Math.min(3, parent.width / 4)
                                        height: 1
                                        radius: 0.5
                                        color: Qt.alpha(Colors.overSurface, 0.45)
                                    }
                                }
                            }
                        }
                        TextEdit {
                            id: answer
                            objectName: "typing-input"
                            // Keep native preedit/selection rendering out of the custom passage.
                            opacity: 0
                            anchors.fill: parent
                            color: "transparent"
                            selectionColor: "transparent"
                            selectedTextColor: "transparent"
                            cursorVisible: false
                            textFormat: TextEdit.PlainText
                            Accessible.name: "Type the passage shown above"
                            selectByMouse: false
                            font: root.readingFont
                            TapHandler { onTapped: { answer.forceActiveFocus(); answer.cursorPosition = answer.length; } }
                            wrapMode: TextEdit.Wrap
                            inputMethodHints: Qt.ImhNoPredictiveText
                            readOnly: root.busy
                            onTextChanged: { root.advance(); root.syncGlyphs(); }
                            onCursorPositionChanged: root.syncCaret()
                            onActiveFocusChanged: {
                                root.speedNow = Date.now();
                                if (!activeFocus) {
                                    root.speedState = TypingSpeed.pause(TypingSpeed.tick(root.speedState, root.speedNow, true));
                                    root.saveProgress();
                                }
                            }
                            Keys.onPressed: event => {
                                if (event.key === Qt.Key_F11) { root.toggleFullscreen(); event.accepted = true; return; }
                                if (event.key === Qt.Key_Backspace && !(event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) && !answer.text.length && !root.busy) {
                                    root.previousPage(); event.accepted = true; return;
                                }
                                if (!root.turningPage || (event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier))) return;
                                if (event.key === Qt.Key_Backspace) { if (root.pendingKeys.length) root.undoQueuedKey(); else if (root.pageDirection > 0) root.backAfterTurn = true; event.accepted = true; }
                                else if (event.text.length && event.text.charCodeAt(0) >= 32) { root.queueTyping(event.text); event.accepted = true; }
                            }
                            Keys.onEscapePressed: event => { root.handleEscape(); event.accepted = true; }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: root.errorMessage || (root.busy ? "Loading…" : (!answer.activeFocus ? "Click the passage to continue typing" : root.chapterTitle)); textFormat: Text.PlainText; color: root.errorMessage ? Colors.error : Colors.overSurface; opacity: root.errorMessage ? 1 : 0.7; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true; Layout.minimumWidth: 0 }
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

                        }
                    }

                }
            }
        }
    }
}
