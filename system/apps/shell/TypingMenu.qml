pragma ComponentBehavior: Bound
import QtQuick
import "TypingTexts.js" as TypingTexts
import "TypingSpeed.js" as TypingSpeed
import "TypingPaging.js" as TypingPaging
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.modules.services as Services
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
    // Bound both typing and reading to one viewport, including while hidden.
    readonly property int layoutLineLimit: Math.max(3, Math.min(36, pageLineLimit))
    onPageLineLimitChanged: fitDelay.restart()
    onReadingFontChanged: { widthCache = ({}); fitDelay.restart(); }
    property var readerPageHistory: []
    property real readerReveal: 1
    property int readerDirection: 1
    property int readerAnimationEvents: 0
    property bool readerHelp: false
    onFullscreenChanged: {
        readerRevealAnimation.stop(); readerReveal = 1; readerHelp = false;
        if (fullscreen) Qt.callLater(() => animateReaderPage(1));
    }
    function animateReaderPage(direction) {
        readerRevealAnimation.stop();
        readerReveal = 1;
        if (!fullscreen || !Motion.enabled) return;
        readerDirection = direction; readerReveal = 0; readerAnimationEvents++;
        readerRevealAnimation.start();
    }
    NumberAnimation {
        id: readerRevealAnimation
        target: root
        property: "readerReveal"
        to: 1
        duration: Motion.enter
        easing.type: Motion.enterCurve
    }
    Connections {
        target: Motion
        function onEnabledChanged() { if (!Motion.enabled) { readerRevealAnimation.stop(); root.readerReveal = 1; } }
    }
    function readerKey(event) {
        if (event.key === Qt.Key_F11) toggleFullscreen();
        else if (event.key === Qt.Key_Escape) handleEscape();
        else if (event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) return false;
        else if (event.key === Qt.Key_L || event.key === Qt.Key_Right || event.key === Qt.Key_PageDown) readNextPage();
        else if (event.key === Qt.Key_H || event.key === Qt.Key_Left || event.key === Qt.Key_PageUp) readPreviousPage();
        else if (event.key === Qt.Key_Space) { if (event.modifiers & Qt.ShiftModifier) readPreviousPage(); else readNextPage(); }
        else if ((event.key === Qt.Key_J || event.key === Qt.Key_BracketRight) && currentChapterIndex + 1 < chapters.length) jumpChapter(currentChapterIndex + 1);
        else if ((event.key === Qt.Key_K || event.key === Qt.Key_BracketLeft) && currentChapterIndex > 0) jumpChapter(currentChapterIndex - 1);
        else if (event.key === Qt.Key_N) openNotebook();
        else if (event.key === Qt.Key_Question) readerHelp = !readerHelp;
        else return false;
        return true;
    }
    function toggleFullscreen() {
        saveProgress();
        readerPageHistory = [];
        fullscreen = !fullscreen;
        stopFeedback();
        fitDelay.restart();
        if (practicing) Qt.callLater(() => root.focusPassage());
    }
    function focusPassage() {
        if (fullscreen) readerText.forceActiveFocus();
        else answer.forceActiveFocus();
    }
    function readNextPage() {
        if (!fullscreen || busy || !bookId || !passage.length) return;
        const next = position + characters(passage).length;
        if (next >= bookLength) return;
        readerPageHistory = readerPageHistory.concat([position]);
        seek(next, true);
    }
    function readPreviousPage() {
        if (!fullscreen || busy || !bookId || position <= 0) return;
        if (readerPageHistory.length) {
            const previous = readerPageHistory[readerPageHistory.length - 1];
            readerPageHistory = readerPageHistory.slice(0, -1);
            seek(previous, true);
        } else {
            historyBack = false;
            send({action: "previous", id: bookId, position: position, loops: 0});
        }
    }
    function readerHtml(value) {
        const escaped = value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        return '<p align="center" style="line-height:155%; margin-top:0px; margin-bottom:0px;">' + escaped + '</p>';
    }
    function readingWordAt(index) {
        const start = passage.lastIndexOf(" ", Math.max(0, index - 1)) + 1;
        const end = passage.indexOf(" ", index);
        return passage.slice(start, end < 0 ? passage.length : end);
    }
    function handleEscape() {
        if (wordPanel.opened) { if (!noteDirty && !noteSaving) wordPanel.close(); else wordMessage = "Save or cancel your changes before returning to reading."; return; }
        if (fullscreen && readerHelp) { readerHelp = false; return; }
        if (fullscreen) { fullscreen = false; fitDelay.restart(); if (practicing) root.focusPassage(); }
        else goBack();
    }
    property bool filePickerActive: false
    property bool resumeOnOpen: false
    property string bookId: ""
    property string bookTitle: ""
    property string bookKind: "book"
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
    property int failureEvents: 0
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
    readonly property bool atChapterStart: bookKind === "book" && currentChapterIndex >= 0
        && position === chapters[currentChapterIndex].position
    property alias wordTools: wordPanel
    property alias readerMenu: readerActions
    property string selectedTerm: ""
    property string wordBookId: ""
    property string savedWordNote: ""
    property string wordMessage: ""
    property string definitionText: ""
    property var notedTerms: []
    property bool noteLoaded: false
    property bool noteSaving: false
    property bool editingWordNote: false
    property bool wordOptionsExpanded: false
    readonly property var noteCategories: ["People", "Settings", "Mysteries", "Plot", "General"]
    property var noteEntries: []
    property bool notebookMode: false
    property bool notebookBrowsing: false
    property bool notebookCreating: false
    property string notebookFilter: "All"
    property string noteCategory: "General"
    property string savedNoteCategory: "General"
    property string newNoteCategory: "General"
    readonly property var visibleNoteEntries: noteEntries.filter(entry =>
        (notebookFilter === "All" || entry.category === notebookFilter) &&
        (!termInput.text.trim() || (entry.term + " " + entry.note).toLowerCase().includes(termInput.text.trim().toLowerCase())))
    readonly property string notePrompt: ({
        "People": "Role & traits:\nRelationships:\nMotives & changes:",
        "Settings": "Place & time:\nAtmosphere:\nRules & important details:",
        "Mysteries": "Question:\nClues:\nTheories:\nAnswer / unresolved:",
        "Plot": "What happened:\nWhy it matters:\nConnections & consequences:",
        "General": "Ideas, quotes, themes, or anything to remember…"
    })[noteCategory]
    property int wordRequest: 0
    property bool definitionsEnabled: false
    property var definitionRequest: null
    property var createDictionaryRequest: () => new XMLHttpRequest()
    readonly property bool noteDirty: wordNote.text !== savedWordNote || noteCategory !== savedNoteCategory
    property Item menuAnchorItem: root
    function currentWordItem() {
        for (let index = 0; index < wordRepeater.count; index++) {
            const item = wordRepeater.itemAt(index);
            if (visualCursor >= item.modelData.start && visualCursor < item.modelData.start + item.modelData.text.length)
                return item;
        }
        return wordRepeater.count ? wordRepeater.itemAt(wordRepeater.count - 1) : null;
    }
    function openCurrentWord() {
        if (wordPanel.opened) { handleEscape(); return; }
        if (fullscreen) { openWord(readerText.selectedText || readingWordAt(readerText.cursorPosition)); return; }
        const item = currentWordItem();
        if (item) openWord(item.modelData.text);
    }
    Shortcut {
        sequence: "Ctrl+Space"
        context: Qt.ApplicationShortcut
        enabled: root.visible && root.practicing && !root.busy && !root.turningPage
        onActivated: root.openCurrentWord()
    }
    function openNotebook() {
        if (wordPanel.opened && (noteDirty || noteSaving)) return;
        openWord(""); notebookMode = true; notebookBrowsing = true; wordOptionsExpanded = false;
        cancelDefinition();
    }
    function beginNotebookNote() {
        if (noteDirty || noteSaving) return;
        openWord(""); notebookMode = true; notebookBrowsing = false; notebookCreating = true;
        wordOptionsExpanded = false;
        newNoteCategory = notebookFilter === "All" ? "General" : notebookFilter;
        Qt.callLater(() => termInput.forceActiveFocus());
    }
    function cancelNoteEdit() {
        wordNote.text = savedWordNote; noteCategory = savedNoteCategory;
        wordMessage = ""; editingWordNote = false;
        if (notebookMode && !savedWordNote) openNotebook();
    }
    function openNotebookEntry(term) {
        if (noteDirty || noteSaving) return;
        const category = notebookCreating ? newNoteCategory : (notebookFilter === "All" ? "General" : notebookFilter);
        openWord(term); notebookMode = true; notebookBrowsing = false;
        newNoteCategory = category;
        cancelDefinition();
    }
    function openWord(value) {
        if (!bookId || (wordPanel.opened && (noteDirty || noteSaving))) return;
        cancelDefinition();
        selectedTerm = value.trim().replace(/^[\s.,!?;:"“”‘’'()[\]{}—–]+|[\s.,!?;:"“”‘’'()[\]{}—–]+$/g, "");
        notedTerms = []; noteEntries = [];
        notebookMode = false; notebookBrowsing = false; notebookCreating = false;
        noteCategory = "General"; savedNoteCategory = "General"; newNoteCategory = "General";
        wordBookId = bookId; noteLoaded = false; noteSaving = false;
        savedWordNote = ""; wordNote.text = ""; wordMessage = "";
        termInput.text = selectedTerm; definitionText = "";
        editingWordNote = false; wordOptionsExpanded = !selectedTerm;
        wordPanel.open();
        wordRequest = requestId + 1;
        if (selectedTerm) {
            send({action: "word", id: wordBookId, term: selectedTerm}, false);
        } else send({action: "words", id: wordBookId}, false);
    }
    function saveWordNote() {
        if (!noteLoaded || noteSaving) return;
        noteSaving = true; wordMessage = "Saving…";
        wordRequest = requestId + 1;
        send({action: "note", id: wordBookId, term: selectedTerm, note: wordNote.text, category: noteCategory}, false);
    }
    function cancelDefinition() {
        definitionTimeout.stop();
        const previous = definitionRequest;
        definitionRequest = null;
        if (previous) previous.abort();
    }
    function lookupDefinition() {
        cancelDefinition(); definitionText = "";
        if (!definitionsEnabled || !selectedTerm || !wordPanel.opened || notebookMode) return;
        definitionText = "Looking up definition…";
        const xhr = createDictionaryRequest(); definitionRequest = xhr;
        xhr.open("GET", "https://api.dictionaryapi.dev/api/v2/entries/en/" + encodeURIComponent(selectedTerm));
        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE || root.definitionRequest !== xhr) return;
            definitionTimeout.stop(); root.definitionRequest = null;
            if (xhr.status === 404) { root.definitionText = "No dictionary entry found. You can still add a note."; return; }
            if (xhr.status !== 200) { root.definitionText = "Dictionary unavailable. Try again when connected."; return; }
            try {
                const entries = JSON.parse(xhr.responseText), lines = [];
                for (const entry of entries.slice(0, 2))
                    for (const meaning of entry.meanings || [])
                        for (const item of (meaning.definitions || []).slice(0, 2))
                            lines.push((meaning.partOfSpeech || "") + " — " + item.definition);
                root.definitionText = lines.slice(0, 8).join("\n\n") || "No definition found.";
            } catch (error) { root.definitionText = "Could not read the dictionary response."; }
        };
        definitionTimeout.start(); xhr.send();
    }
    Timer { id: definitionTimeout; interval: 10000; onTriggered: { root.cancelDefinition(); root.definitionText = "Dictionary timed out. Try again."; } }
    function characters(value) {
        return value.match(/[\uD800-\uDBFF][\uDC00-\uDFFF]|[\s\S]/g) ?? [];
    }
    readonly property string displayedInput: TypingPaging.displayInput(answer.text, passage)
    onDisplayedInputChanged: syncGlyphs()
    onVisualCursorChanged: syncCaret()
    readonly property int visualCursor: Math.min(TypingPaging.displayInput(answer.text.slice(0, answer.cursorPosition), passage).length, passage.length - 1)
    readonly property real progress: bookLength ? Math.min(1, (position + characters(displayedInput).length) / bookLength) : 0
    readonly property var passageWords: pageLayout.words
    readonly property font readingFont: Qt.font({family: Config.theme.font, pixelSize: fullscreen ? 20 : Config.theme.fontSize + 2, weight: Font.Normal})
    FontMetrics { id: typingMetrics; font: root.readingFont }
    readonly property rect highlightBounds: {
        const metricsFont = typingMetrics.font;
        return typingMetrics.tightBoundingRect("Hg");
    }
    readonly property real highlightPadding: 3
    readonly property real letterPadding: 1
    property var widthCache: ({})
    function characterWidth(text) {
        if (widthCache[text] === undefined)
            widthCache[text] = Math.max(1, Math.ceil(typingMetrics.advanceWidth(text)));
        return widthCache[text];
    }
    function fitPage() {
        // A direct fit also satisfies any pending resize/font fit.
        fitDelay.stop();
        stopFeedback();
        scrollLine = -1;
        passageVisuals.contentY = 0;
        pageLayout = TypingPaging.layout(pageSource, Math.max(1, passageFlow.width), characterWidth, layoutLineLimit);
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
        onTriggered: { if (root.visible && root.practicing && passageArea.width > 0 && passageArea.height > 0 && !root.restoring && root.pageSource.length) { root.fitPage(); if (!root.fullscreen && root.bookId && root.characters(answer.text).length >= root.characters(root.passage).length) root.advance(); } }
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
        if (kind === "letter" || kind === "error") {
            if (!glyph) return;
            // Each keystroke finishes its own fade, even during the next key or row.
            glyph.stopFeedback();
            if (glowingGlyphs.length >= 12) glowingGlyphs[0].stopFeedback();
            glowingGlyphs = glowingGlyphs.concat([glyph]);
            if (kind === "error") failureEvents++; else feedbackEvents++;
            glyph.startFeedback(kind === "error");
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
    implicitHeight: 600
    onPracticingChanged: { resetSpeed(); syncCaret(); }
    onVisibleChanged: {
        if (visible) { backendStarted = true; if (ready) send({action: "list"}, false); }
        else { saveProgress(); stopFeedback(); }
        resetSpeed();
        if (visible && practicing) { fitDelay.restart(); Qt.callLater(() => root.focusPassage()); }
    }
    Component.onCompleted: { if (visible) backendStarted = true; }
    function send(data, page = true) {
        // Request enough for one measured page, never a whole paragraph/chapter.
        const narrowWidth = Math.min(characterWidth("i"), characterWidth(" "));
        data.window = Math.max(512, Math.min(4096,
            Math.ceil(Math.max(640, passageFlow.width) / narrowWidth) * layoutLineLimit + 72));
        data.paragraphs = false;
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
        const previousInput = glyph.enteredCharacter;
        glyph.typed = glyph.characterIndex < displayedInput.length;
        glyph.incorrect = glyph.typed && !TypingPaging.matchingCharacter(displayedInput.substr(glyph.characterIndex, glyph.modelData.length), glyph.modelData);
        glyph.enteredCharacter = glyph.typed ? displayedInput.substr(glyph.characterIndex, glyph.modelData.length) : "";
        glyph.caretHere = practicing && glyph.characterIndex === visualCursor;
        if (!glyph.incorrect && glyph.failedFeedback) glyph.stopFeedback();
        if (!glyph.typed) glyph.stopFeedback();
        else if (glyph.incorrect) {
            if (previousInput !== glyph.enteredCharacter) {
                glyph.stopFeedback();
                if (glyph.initialized && !restoring && !busy && visible && practicing && answer.activeFocus && Motion.enabled)
                    requestFeedback("error", glyph);
            }
        }
        else if (!wasCorrect && glyph.initialized && !restoring && !busy && visible && practicing && answer.activeFocus && Motion.enabled && glyph.modelData.trim().length)
            glyph.celebrate();
    }
    property int scrollLine: -1
    function syncCaret() {
        const previous = renderedCaret;
        // Move the viewport before creating glyphs for a distant cursor jump.
        if (practicing && !fullscreen) {
            const words = pageLayout.words;
            let low = 0, high = words.length - 1, line = 0;
            while (low <= high) {
                const middle = (low + high) >> 1;
                if (words[middle].start <= visualCursor) { line = words[middle].line; low = middle + 1; }
                else high = middle - 1;
            }
            // Only reposition for a new row or a cursor outside the viewport.
            // Same-row keystrokes must not fight manual scrolling or churn delegates.
            const rowY = line * passageLineHeight;
            const caretY = rowY + passageVisuals.centerPadding;
            if (line !== scrollLine || caretY < passageVisuals.contentY
                    || caretY + passageLineHeight > passageVisuals.contentY + passageVisuals.height)
                passageVisuals.contentY = Math.max(0, Math.min(rowY, passageVisuals.contentHeight - passageVisuals.height));
            scrollLine = line;
        }
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
        running: root.visible && root.practicing && !root.fullscreen && !root.busy && answer.activeFocus
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
    property string pendingDeleteId: ""
    property string pendingDeleteTitle: ""
    property string deleteMessage: ""
    property int deleteRequest: 0
    function requestBookDeletion(id, title) {
        if (busy) return;
        pendingDeleteId = id; pendingDeleteTitle = title; deleteMessage = "";
    }
    function confirmBookDeletion() {
        if (!pendingDeleteId || busy) return;
        if (pendingDeleteId === bookId) { saveProgress(); saveDelay.stop(); dirty = false; }
        busy = true; deleteMessage = "";
        deleteRequest = requestId + 1;
        send({action: "delete", id: pendingDeleteId, confirmed: true}, false);
    }
    function openBook(id) {
        if (busy) return;
        saveProgress(); draft = false; resumeOnOpen = true;
        send({action: "open", id: id});
    }
    function seek(offset, preserveReaderHistory = false) {
        if (!bookId || busy) return;
        if (!preserveReaderHistory) readerPageHistory = [];
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
        readerPageHistory = [];
        dirty = false;
        send({action: "chapter", id: bookId, index: index, loops: rounds});
    }
    function receive(line) {
        try {
            const data = JSON.parse(line);
            if (data.action === "delete") {
                if (data.request !== deleteRequest) return;
                busy = false;
                if (data.error) { deleteMessage = data.error; return; }
                library = data.books || []; pendingDeleteId = ""; pendingDeleteTitle = "";
                if (bookId === data.deleted) {
                    saveDelay.stop(); dirty = false; restoring = true;
                    wordPanel.close(); bookId = ""; bookTitle = ""; bookLength = 0;
                    position = 0; rounds = 0; chapters = []; pageSource = "";
                    pageLayout = {text: "", words: [], lines: 0, lineWidths: []};
                    answer.text = ""; pageHistory = []; readerPageHistory = [];
                    selectedTerm = ""; wordBookId = ""; savedWordNote = ""; wordNote.text = "";
                    noteCategory = "General"; savedNoteCategory = "General"; notedTerms = []; noteEntries = [];
                    noteLoaded = false; editingWordNote = false; notebookMode = false;
                    practicing = false; fullscreen = false; draft = false; restoring = false;
                    resetPageCaret(); resetSpeed();
                }
                message = "Book removed from your library.";
                return;
            }
            if (["words", "word", "note", "word_settings"].indexOf(data.action) >= 0) {
                if (data.action === "word_settings") {
                    if (!data.error) { definitionsEnabled = data.enabled; lookupDefinition(); }
                    else wordMessage = data.error;
                    return;
                }
                if (data.request !== wordRequest) return;
                noteSaving = false;
                if (data.error) { wordMessage = data.error; return; }
                if (data.id !== wordBookId) return;
                if (data.action === "words") { notedTerms = data.terms || []; noteEntries = data.entries || []; return; }
                selectedTerm = data.term; savedWordNote = data.note; wordNote.text = data.note;
                notedTerms = data.terms || []; noteEntries = data.entries || []; noteLoaded = true;
                savedNoteCategory = data.note ? (data.category || "General") : newNoteCategory;
                noteCategory = savedNoteCategory;
                wordMessage = "";
                if (data.action === "note") editingWordNote = false;
                if (data.action === "word") {
                    if (notebookMode && !data.note) { editingWordNote = true; Qt.callLater(() => wordNote.forceActiveFocus()); }
                    lookupDefinition();
                }
                return;
            }
            if (data.action === "list") { if (data.books) library = data.books; return; }
            if (data.error) { if (data.request === pageRequest) { busy = false; turningPage = false; historyBack = false; backAfterTurn = false; } if (data.action === "save") dirty = true; message = data.error; errorMessage = data.error; return; }
            if (data.request !== pageRequest) return;
            if (data.atBeginning) { busy = false; turningPage = false; return; }
            if (data.previousText !== undefined) {
                let offset = 0, last = 0, text = "";
                while (offset < data.previousText.length) {
                    last = offset;
                    text = TypingPaging.layout(data.previousText.slice(offset), Math.max(1, passageFlow.width), characterWidth, layoutLineLimit).text;
                    if (!text.length) break;
                    offset += text.length;
                }
                send({action: "previous", id: bookId, resolved: true,
                    position: data.previousStart + characters(data.previousText.slice(0, last)).length,
                    typed: fullscreen ? "" : characters(text).slice(0, -1).join(""), loops: data.loops});
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
            const fitted = TypingPaging.layout(data.passage, Math.max(1, passageFlow.width), characterWidth, layoutLineLimit);
            const prepared = TypingPaging.prepareInput(data.typed, fitted.text);
            data.typed = prepared.text;
            const entered = characters(data.typed);
            const pageCount = characters(fitted.text).length;
            if (!fullscreen && data.action !== "next" && data.action !== "previous" && pageCount > 0 && entered.length >= pageCount && !prepared.pending) {
                restoreAction = data.action;
                restoreChapters = data.chapters || chapters;
                const next = data.position + pageCount;
                send({action: "next", id: data.id, position: next >= data.length ? 0 : next,
                    typed: entered.slice(pageCount).join(""), loops: data.loops + (next >= data.length ? 1 : 0)});
                return;
            }
            restoreAction = ""; restoreChapters = [];
            if (data.action === "next" && !fullscreen) {
                speedCommitted += Math.max(0, correctCount() - speedBaseline);
                speedBaseline = 0;
                speedState = TypingSpeed.pause(speedState);
            }
            if (bookId !== data.id || ["seek", "chapter", "open", "add", "import"].indexOf(data.action) >= 0) pageHistory = [];
            if (data.action === "previous") {
                pageHistory = historyBack ? pageHistory.slice(0, -1) : [];
                historyBack = false;
            }
            if (bookId !== data.id || ["open", "add", "import"].indexOf(data.action) >= 0) readerPageHistory = [];
            const readerMoved = bookId !== data.id || position !== data.position;
            const revealDirection = data.position < position ? -1 : 1;
            restoring = true;
            bookId = data.id; bookTitle = data.title; bookKind = data.kind || "book"; bookLength = data.length;
            position = data.position; rounds = data.loops; if (data.chapters) chapters = data.chapters;
            resetPageCaret();
            pageSource = data.passage; fitPage();
            answer.text = data.typed; answer.cursorPosition = answer.length;
            dirty = false; draft = false; busy = false; restoring = false;
            turningPage = false;
            if (fullscreen && readerMoved) animateReaderPage(revealDirection);
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
            if (practicing && visible) Qt.callLater(() => root.focusPassage());
            if (data.action !== "next") send({action: "list"}, false);
        } catch (error) { busy = false; message = "Could not read the book service response."; }
    }
    Timer { id: saveDelay; interval: 650; onTriggered: root.saveProgress() }
    Timer { interval: 5000; running: root.backendStarted; repeat: true; onTriggered: root.saveProgress() }

    function status() {
        return JSON.stringify({readingMode: fullscreen, readerAnimationEvents: readerAnimationEvents, readerMotionEnabled: Motion.enabled, chapterCardVisible: chapterCard.visible, chapterTitle: chapterTitle, wordToolsOpen: wordPanel.opened, wordMenuReveal: wordPanel.reveal, wordMenuOpenAnimations: wordPanel.openAnimations, wordMenuCloseAnimations: wordPanel.closeAnimations, noteDirty: noteDirty, noteSaving: noteSaving, wordToolsShortcut: "Ctrl+Space", wordMenuWidth: wordPanel.width, wordMenuHeight: wordPanel.height, typingPanelWidth: menuAnchorItem.width, typingPanelHeight: menuAnchorItem.height, notebookMode: notebookMode, notebookCreating: notebookCreating, notesSection: notebookFilter, definitionsEnabled: definitionsEnabled, notedWordCount: notedTerms.length, practicing: practicing, fullscreen: fullscreen, pageLines: pageLayout.lines, pageLineLimit: pageLineLimit, passageHeight: passageArea.height, renderedHeight: passageFlow.height, fontSize: readingFont.pixelSize, layoutVersion: 9, previousPages: pageHistory.length, activeEffects: activeEffects, effectKind: effectKind, lineTransitions: lineTransitions, pageTransitions: pageTransitions, motionEnabled: Motion.enabled, feedbackEvents: feedbackEvents, focused: answer.activeFocus, turningPage: turningPage, textLength: bookLength,
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
    component PrimaryTextButton: TextButton {
        id: primaryButton
        implicitHeight: 40
        padding: 12
        background: StyledRect { id: primarySurface; variant: primaryButton.down ? "primaryfocus" : "primary"; radius: 12 }
        contentItem: StyledText { text: primaryButton.text; color: primarySurface.item; opacity: primaryButton.enabled ? 1 : 0.4; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
    }
    component ReaderNavButton: TextButton {
        id: nav
        implicitHeight: 40
        implicitWidth: 100
        background: StyledRect {
            variant: nav.hovered || nav.activeFocus ? "focus" : "pane"
            radius: 16
            backgroundOpacity: nav.enabled ? 0.75 : 0.25
        }
    }
    component ReaderAction: MenuItem {
        id: action
        implicitHeight: 40
        contentItem: StyledText {
            text: action.text
            opacity: action.enabled ? 1 : 0.35
            color: action.highlighted ? Colors.primary : Colors.overSurface
            verticalAlignment: Text.AlignVCenter
        }
        background: StyledRect { variant: action.highlighted ? "focus" : "transparent"; radius: 8 }
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
        if (bookId) { practicing = true; root.focusPassage(); }
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
        } else { practicing = true; root.focusPassage(); }
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
        if (fullscreen) return;
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
            root.send({action: "word_settings"}, false);
        }
        stdout: SplitParser { onRead: line => root.receive(line) }
        onExited: {
            root.ready = false; root.backendStarted = false; root.busy = false;
            root.message = "Book service stopped. Reopen typing to reconnect."; root.errorMessage = root.message;
        }
    }
    PopupWindow {
        id: wordPanel
        objectName: "typing-word-panel"
        anchor.item: root.menuAnchorItem
        anchor.rect.x: 0
        anchor.rect.y: root.menuAnchorItem.height + 6
        anchor.rect.width: 0
        anchor.rect.height: 0
        implicitWidth: Math.max(1, root.menuAnchorItem.width)
        implicitHeight: Math.max(1, root.menuAnchorItem.height)
        color: "transparent"
        visible: false
        property bool opened: false
        property real reveal: 0
        property int openAnimations: 0
        property int closeAnimations: 0
        readonly property real availableWidth: width - 32
        property alias surface: wordPanelSurface
        mask: Region { item: panelViewport }
        function open() {
            const wasOpen = opened;
            panelMotion.stop(); opened = true; visible = true;
            if (!wasOpen && Motion.enabled) {
                openAnimations++; panelMotion.to = 1; panelMotion.duration = Motion.enter; panelMotion.start();
            } else reveal = 1;
            Qt.callLater(() => { if (root.wordOptionsExpanded || root.notebookCreating) termInput.forceActiveFocus(); else contentItem.forceActiveFocus(); });
        }
        function close() {
            if (!opened) return;
            opened = false; panelMotion.stop(); root.cancelDefinition();
            if (root.practicing) root.focusPassage();
            if (Motion.enabled) {
                closeAnimations++; panelMotion.to = 0; panelMotion.duration = Motion.exit; panelMotion.start();
            } else { reveal = 0; visible = false; }
        }
        NumberAnimation {
            id: panelMotion
            target: wordPanel
            property: "reveal"
            easing.type: Motion.enterCurve
            onFinished: { if (!wordPanel.opened) wordPanel.visible = false; }
        }
        Connections {
            target: Motion
            function onEnabledChanged() {
                if (!Motion.enabled) { panelMotion.stop(); wordPanel.reveal = wordPanel.opened ? 1 : 0; if (!wordPanel.opened) wordPanel.visible = false; }
            }
        }
        onVisibleChanged: { if (!visible) { panelMotion.stop(); opened = false; reveal = 0; root.cancelDefinition(); } }
        Services.FocusGrab {
            active: wordPanel.opened
            windows: [wordPanel]
            onCleared: { if (!root.noteDirty && !root.noteSaving) wordPanel.close(); }
        }
        Item {
            id: panelViewport
            width: wordPanel.width
            height: wordPanel.height * wordPanel.reveal
            clip: true
            Item {
                id: panelSheet
                objectName: "typing-notes-sheet"
                width: wordPanel.width
                height: wordPanel.height
                enabled: wordPanel.opened
                opacity: 0.65 + 0.35 * wordPanel.reveal
                transform: Translate { y: -24 * (1 - wordPanel.reveal) }
                StyledRect {
                    id: wordPanelSurface
                    objectName: "typing-word-panel-surface"
                    anchors.fill: parent
                    variant: "bg"
                    radius: 16
                    border.width: 1
                    border.color: Qt.alpha(Colors.primary, 0.28)
                }
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        TextButton { objectName: "typing-notebook-back"; visible: root.notebookMode && !root.notebookBrowsing; text: "‹ Notes"; enabled: !root.noteDirty && !root.noteSaving; onClicked: root.openNotebook() }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            StyledText { visible: root.fullscreen; text: root.notebookMode ? "BOOK NOTEBOOK" : "WORD NOTES"; font.pixelSize: 10; font.letterSpacing: 2; color: Colors.primary }
                            StyledText {
                                text: root.notebookBrowsing ? "Book notes" : (root.notebookCreating ? "New note" : (root.selectedTerm || "Word lookup"))
                                textFormat: Text.PlainText
                                font.family: Config.theme.font
                                font.pixelSize: root.fullscreen ? 24 : 16
                                font.weight: Font.DemiBold
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            StyledText { visible: root.fullscreen; text: root.bookTitle; textFormat: Text.PlainText; opacity: 0.5; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                        }
                        TextButton { text: "Return to reading"; enabled: !root.noteDirty && !root.noteSaving; onClicked: wordPanel.close() }
                    }
                    ScrollView {
                        objectName: "typing-word-scroll"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: availableWidth
                        ColumnLayout {
                            id: wordContent
                            width: wordPanel.availableWidth - 12
                            spacing: 8
                            Keys.onEscapePressed: event => { root.handleEscape(); event.accepted = true; }
                            RowLayout {
                                objectName: "typing-word-search"
                                visible: root.notebookBrowsing || root.notebookCreating || (root.wordOptionsExpanded && !root.notebookMode)
                                Layout.fillWidth: true
                                TextField {
                                    id: termInput
                                    objectName: "typing-word-term"
                                    Layout.fillWidth: true
                                    maximumLength: 120
                                    implicitHeight: 48
                                    padding: 12
                                    placeholderText: root.notebookBrowsing ? "Search your notes" : (root.notebookCreating ? "Title, e.g. Elliot or the missing letter" : "Word to look up")
                                    color: Colors.overSurface
                                    font: Qt.font({family: Config.theme.font, pixelSize: root.fullscreen ? 16 : root.readingFont.pixelSize})
                                    placeholderTextColor: Qt.alpha(Colors.overSurface, 0.35)
                                    selectionColor: Qt.alpha(Colors.primary, 0.3)
                                    selectedTextColor: Colors.overSurface
                                    selectByMouse: true
                                    enabled: !root.noteDirty && !root.noteSaving
                                    background: StyledRect { variant: "pane"; radius: 8; border.width: 1; border.color: termInput.activeFocus ? Colors.primary : Colors.outlineVariant }
                                    onAccepted: { if (!root.notebookBrowsing) { if (root.notebookCreating) root.openNotebookEntry(text); else root.openWord(text); } }
                                }
                                PrimaryTextButton {
                                    text: root.notebookBrowsing ? "New note" : (root.notebookCreating ? "Create note" : "Look up")
                                    objectName: "typing-new-notebook-note"
                                    enabled: (root.notebookBrowsing || termInput.text.trim().length > 0) && !root.noteDirty && !root.noteSaving
                                    onClicked: { if (root.notebookBrowsing) root.beginNotebookNote(); else if (root.notebookCreating) root.openNotebookEntry(termInput.text); else root.openWord(termInput.text); }
                                }
                            }
                            StyledText { visible: root.notebookCreating; text: "Choose a section"; font.pixelSize: 12 }
                            ThemeSelect {
                                visible: root.notebookCreating
                                Layout.fillWidth: true
                                textRole: ""
                                model: root.noteCategories
                                currentIndex: root.noteCategories.indexOf(root.newNoteCategory)
                                onActivated: index => root.newNoteCategory = root.noteCategories[index]
                            }
                            Flow {
                                visible: root.notebookBrowsing
                                Layout.fillWidth: true
                                spacing: 4
                                Repeater {
                                    model: ["All"].concat(root.noteCategories)
                                    delegate: Button {
                                        id: sectionTab
                                        required property string modelData
                                        implicitHeight: 36
                                        leftPadding: 12
                                        rightPadding: 12
                                        text: modelData
                                        Accessible.name: modelData + " notes"
                                        background: StyledRect { variant: root.notebookFilter === sectionTab.modelData ? "focus" : "pane"; radius: 10; border.width: 1; border.color: root.notebookFilter === sectionTab.modelData ? Qt.alpha(Colors.primary, 0.6) : "transparent" }
                                        contentItem: StyledText { text: sectionTab.text; color: root.notebookFilter === sectionTab.modelData ? Colors.primary : Colors.overSurface; opacity: root.notebookFilter === sectionTab.modelData ? 1 : 0.65; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter }
                                        onClicked: root.notebookFilter = modelData
                                    }
                                }
                            }
                            RowLayout {
                                visible: root.fullscreen && root.notebookBrowsing
                                Layout.fillWidth: true
                                Layout.topMargin: 8
                                StyledText { text: root.notebookFilter === "All" ? "All notes" : root.notebookFilter; font.pixelSize: 22; font.weight: Font.DemiBold; Layout.fillWidth: true }
                                StyledText { text: root.visibleNoteEntries.length + (root.visibleNoteEntries.length === 1 ? " note" : " notes"); font.pixelSize: 12; opacity: 0.5 }
                            }
                            GridLayout {
                                id: notesGrid
                                objectName: "typing-notebook-entries"
                                columns: root.fullscreen && wordPanel.width >= 760 ? 2 : 1
                                columnSpacing: 12
                                rowSpacing: 12
                                visible: root.notebookBrowsing
                                Layout.fillWidth: true
                                StyledText {
                                    Layout.columnSpan: notesGrid.columns
                                    visible: root.visibleNoteEntries.length === 0
                                    text: termInput.text.trim() ? "No matching notes. Try another search." : "No notes in this section. Choose New note to start."
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                    Layout.fillWidth: true
                                }
                                Repeater {
                                    model: root.visibleNoteEntries
                                    delegate: StyledRect {
                                        id: notebookEntryCard
                                        required property var modelData
                                        objectName: "typing-notebook-entry-" + modelData.term
                                        Layout.fillWidth: true
                                        implicitHeight: Math.max(root.fullscreen ? 120 : 86, entryContent.implicitHeight + 28)
                                        variant: "pane"
                                        radius: 12
                                        backgroundOpacity: entryHover.hovered || activeFocus ? 0.75 : 0.4
                                        border.width: 1
                                        border.color: entryHover.hovered || activeFocus ? Qt.alpha(Colors.primary, 0.6) : Qt.alpha(Colors.outlineVariant, 0.35)
                                        HoverHandler { id: entryHover }
                                        activeFocusOnTab: true
                                        Accessible.name: modelData.term
                                        Accessible.role: Accessible.Button
                                        Keys.onReturnPressed: root.openNotebookEntry(modelData.term)
                                        TapHandler { onTapped: root.openNotebookEntry(notebookEntryCard.modelData.term) }
                                        ColumnLayout {
                                            id: entryContent
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.margins: 14
                                            spacing: 8
                                            StyledText { text: notebookEntryCard.modelData.category.toUpperCase(); color: Colors.primary; font.pixelSize: 10; font.letterSpacing: 1.5; Layout.fillWidth: true }
                                            StyledText { text: notebookEntryCard.modelData.term; textFormat: Text.PlainText; font.pixelSize: root.fullscreen ? 18 : 14; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                                            StyledText { text: notebookEntryCard.modelData.note; textFormat: Text.PlainText; opacity: 0.65; font.pixelSize: root.fullscreen ? 14 : 12; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight; Layout.fillWidth: true }
                                        }
                                    }
                                }
                            }
                            ThemeSelect {
                                textRole: ""
                                objectName: "typing-saved-words"
                                Layout.fillWidth: true
                                visible: !root.notebookMode && root.wordOptionsExpanded && root.notedTerms.length > 0
                                model: root.notedTerms
                                displayText: "Saved notes in this book"
                                enabled: !root.noteDirty && !root.noteSaving
                                onActivated: index => root.openWord(root.notedTerms[index])
                            }
                            TextButton {
                                objectName: "typing-definitions-toggle"
                                visible: !root.notebookMode && root.wordOptionsExpanded
                                text: "Online definitions: " + (root.definitionsEnabled ? "On" : "Off")
                                onClicked: {
                                    root.definitionsEnabled = !root.definitionsEnabled;
                                    root.cancelDefinition(); root.definitionText = "";
                                    root.send({action: "word_settings", enabled: root.definitionsEnabled}, false);
                                }
                            }
                            ScrollView {
                                Layout.fillWidth: true
                                Layout.preferredHeight: Math.min(160, definitionLabel.implicitHeight)
                                visible: !root.notebookMode && root.definitionsEnabled && root.selectedTerm.length > 0
                                clip: true
                                StyledText { id: definitionLabel; width: wordPanel.availableWidth - 12; text: root.definitionText; textFormat: Text.PlainText; wrapMode: Text.Wrap; font.pixelSize: 12 }
                            }
                            RowLayout {
                                visible: !root.notebookMode && root.wordOptionsExpanded && root.definitionsEnabled
                                StyledText { text: "English definitions · Free Dictionary API"; font.pixelSize: 11; opacity: 0.65 }
                                TextButton { text: "Retry"; enabled: root.selectedTerm.length > 0; onClicked: root.lookupDefinition() }
                            }
                            StyledText {
                                objectName: "typing-word-note-preview"
                                visible: !root.editingWordNote && root.savedWordNote.length > 0
                                text: root.savedWordNote
                                textFormat: Text.PlainText
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                                color: Colors.overSurface
                                font.pixelSize: 12
                            }
                            TextButton {
                                objectName: "typing-edit-word-note"
                                visible: !root.editingWordNote && root.selectedTerm.length > 0
                                enabled: root.noteLoaded
                                text: root.savedWordNote.length ? "Edit note" : "Add note"
                                onClicked: { root.editingWordNote = true; wordNote.forceActiveFocus(); }
                            }
                            StyledText { visible: root.savedWordNote.length > 0 && !root.editingWordNote; text: root.savedNoteCategory; color: Colors.primary; font.pixelSize: 11 }
                            ThemeSelect {
                                objectName: "typing-note-category"
                                visible: root.editingWordNote
                                Layout.fillWidth: true
                                textRole: ""
                                model: root.noteCategories
                                currentIndex: root.noteCategories.indexOf(root.noteCategory)
                                enabled: !root.noteSaving
                                onActivated: index => root.noteCategory = root.noteCategories[index]
                            }
                            TextButton {
                                objectName: "typing-note-template"
                                visible: root.editingWordNote && root.noteCategory !== "General" && !wordNote.text.length
                                text: "Insert outline"
                                onClicked: { wordNote.text = root.notePrompt + "\n"; wordNote.forceActiveFocus(); }
                            }
                            ScrollView {
                                visible: root.editingWordNote
                                Layout.fillWidth: true
                                Layout.preferredHeight: root.fullscreen ? Math.max(160, Math.min(420, wordPanel.height * 0.35)) : 110
                                Layout.minimumHeight: 55
                                TextArea {
                                    id: wordNote
                                    objectName: "typing-word-note"
                                    enabled: root.noteLoaded && !root.noteSaving
                                    textFormat: TextEdit.PlainText
                                    placeholderText: root.notePrompt
                                    padding: root.fullscreen ? 16 : 10
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    color: Colors.overSurface
                                    font: Qt.font({family: Config.theme.font, pixelSize: root.fullscreen ? 18 : root.readingFont.pixelSize})
                                    placeholderTextColor: Qt.alpha(Colors.overSurface, 0.35)
                                    selectionColor: Qt.alpha(Colors.primary, 0.3)
                                    selectedTextColor: Colors.overSurface
                                    background: StyledRect { variant: "pane"; radius: 8 }
                                    Accessible.name: "Note for selected word or name"
                                }
                            }
                            StyledText { visible: text.length > 0; text: wordNote.length > 10000 ? "Notes can contain up to 10,000 characters." : (root.noteSaving ? "" : root.wordMessage); textFormat: Text.PlainText; wrapMode: Text.Wrap; Layout.fillWidth: true; font.pixelSize: 11 }
                            TextButton {
                                objectName: "typing-word-options"
                                visible: !root.notebookMode
                                text: root.wordOptionsExpanded ? "Hide dictionary options" : "Dictionary options"
                                onClicked: root.wordOptionsExpanded = !root.wordOptionsExpanded
                            }
                        }
                    }
                    RowLayout {
                        objectName: "typing-note-actions"
                        visible: root.editingWordNote
                        Layout.fillWidth: true
                        StyledText { text: root.noteSaving ? "Saving…" : (root.noteDirty ? "Unsaved changes" : ""); font.pixelSize: 11; Layout.fillWidth: true }
                        TextButton { objectName: "typing-cancel-note-edit"; text: "Cancel"; enabled: !root.noteSaving; onClicked: root.cancelNoteEdit() }
                        PrimaryTextButton { objectName: "typing-save-word-note"; text: "Save note"; enabled: root.noteLoaded && root.noteDirty && !root.noteSaving && wordNote.length <= 10000; onClicked: root.saveWordNote() }
                    }
                }
            }
        }
    }
    Item {
        anchors.fill: parent
        ColumnLayout {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.topMargin: root.fullscreen ? 32 : (root.practicing ? 12 : 20)
            anchors.bottomMargin: root.fullscreen ? 28 : (root.practicing ? 12 : 20)
            width: root.fullscreen ? Math.min(720, Math.max(1, parent.width - 80)) : Math.max(1, parent.width - (root.practicing ? 48 : 40))
            spacing: root.fullscreen ? 20 : 12
            RowLayout {
                Layout.fillWidth: true
                Layout.maximumHeight: 36
                StyledText { text: root.practicing ? root.bookTitle : "Your book library"; textFormat: Text.PlainText; elide: Text.ElideRight; Layout.minimumWidth: 0; font.pixelSize: root.fullscreen ? 13 : 18; font.letterSpacing: root.fullscreen ? 0.7 : 0; opacity: root.fullscreen ? 0.5 : 0.65; Layout.fillWidth: true }
                TextButton { objectName: "typing-book-notebook"; text: "Notes"; visible: root.practicing; enabled: !!root.bookId && !root.busy; onClicked: root.openNotebook() }
                TextButton {
                    id: readerActionsButton
                    objectName: "typing-reader-actions"
                    text: "⋯"
                    implicitWidth: 36
                    Accessible.name: "Reader actions"
                    onClicked: readerActions.open()
                    Menu {
                        id: readerActions
                        x: readerActionsButton.width - width
                        y: readerActionsButton.height + 4
                        width: 220
                        padding: 6
                        background: StyledRect { variant: "bg"; radius: 12; border.width: 1; border.color: Qt.alpha(Colors.primary, 0.28) }
                        ReaderAction { objectName: "typing-fullscreen"; text: root.fullscreen ? "Typing mode · F11" : "Reading mode · F11"; onClicked: { readerActions.close(); root.toggleFullscreen(); } }
                        ReaderAction { objectName: "typing-library"; text: "Book library"; enabled: root.practicing; onClicked: { readerActions.close(); root.showLibrary(); } }
                        ReaderAction { objectName: "typing-reader-import"; text: "Import book…"; enabled: !root.busy; onClicked: { readerActions.close(); root.openImport(); } }
                    }
                }
                TextButton { objectName: "typing-back"; visible: !root.practicing; text: "Back"; enabled: !root.busy && (root.bookId.length > 0 || root.draft || root.library.length > 0); onClicked: root.goBack() }
                TextButton { visible: root.fullscreen; text: "Exit reading"; onClicked: root.toggleFullscreen() }
                TextButton { visible: !root.fullscreen; text: "Close"; onClicked: { root.saveProgress(); root.backRequested(); } }
            }
            Rectangle { visible: root.fullscreen; Layout.fillWidth: true; implicitHeight: 1; color: Qt.alpha(Colors.outlineVariant, 0.4) }
            StyledText {
                visible: root.fullscreen && !root.atChapterStart
                text: root.chapterTitle
                textFormat: Text.PlainText
                font.pixelSize: 12
                font.letterSpacing: 1.5
                color: Qt.alpha(Colors.primary, 0.7)
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
                elide: Text.ElideRight
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
                StyledRect {
                    objectName: "typing-delete-confirmation"
                    visible: !root.practicing && root.pendingDeleteId.length > 0
                    Layout.fillWidth: true
                    implicitHeight: deleteContent.implicitHeight + 24
                    variant: "pane"
                    radius: 12
                    border.width: 1
                    border.color: Qt.alpha(Colors.error, 0.5)
                    ColumnLayout {
                        id: deleteContent
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 8
                        StyledText { text: 'Remove “' + root.pendingDeleteTitle + '”?'; textFormat: Text.PlainText; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        StyledText { text: "This removes its saved progress and notes. The original file stays on disk."; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        StyledText { visible: root.deleteMessage.length > 0; text: root.deleteMessage; textFormat: Text.PlainText; color: Colors.error; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        RowLayout {
                            Item { Layout.fillWidth: true }
                            TextButton { objectName: "typing-cancel-delete"; text: "Cancel"; enabled: !root.busy; onClicked: { root.pendingDeleteId = ""; root.deleteMessage = ""; } }
                            TextButton { objectName: "typing-confirm-delete"; text: root.busy ? "Removing…" : "Remove book"; enabled: !root.busy; onClicked: root.confirmBookDeletion() }
                        }
                    }
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
                                TextButton { objectName: "typing-delete-book"; text: "Remove"; enabled: !root.busy; Accessible.name: "Remove " + bookCard.modelData.title; onClicked: root.requestBookDeletion(bookCard.modelData.id, bookCard.modelData.title) }
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
                    StyledRect {
                        id: chapterCard
                        objectName: "typing-chapter-card"
                        visible: root.atChapterStart
                        Layout.fillWidth: true
                        implicitHeight: chapterCardText.implicitHeight + (root.fullscreen ? 48 : 28)
                        variant: root.fullscreen ? "transparent" : "pane"
                        radius: 16
                        border.width: 1
                        border.color: root.fullscreen ? "transparent" : Qt.alpha(Colors.primary, 0.35)
                        ColumnLayout {
                            id: chapterCardText
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.margins: 18
                            spacing: 6
                            StyledText {
                                text: (root.fullscreen ? "CHAPTER · " : "NEW CHAPTER · ") + (root.currentChapterIndex + 1) + " / " + root.chapters.length
                                color: Colors.primary
                                font.pixelSize: 11
                                font.letterSpacing: root.fullscreen ? 2.5 : 1.2
                                horizontalAlignment: root.fullscreen ? Text.AlignHCenter : Text.AlignLeft
                                Layout.fillWidth: true
                            }
                            StyledText {
                                objectName: "typing-chapter-card-title"
                                text: root.chapterTitle
                                textFormat: Text.PlainText
                                font.family: Config.theme.font
                                font.pixelSize: root.fullscreen ? 40 : 26
                                font.weight: root.fullscreen ? Font.Normal : Font.DemiBold
                                horizontalAlignment: root.fullscreen ? Text.AlignHCenter : Text.AlignLeft
                                color: Colors.overSurface
                                wrapMode: Text.Wrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }
                    }
                    Item {
                        id: passageArea
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: Math.min(3 * root.passageLineHeight, root.height / 3)
                        clip: true
                        onWidthChanged: {
                            if (root.pageSource.length) fitDelay.restart();
                            Qt.callLater(() => { if (smoothCaret.targetGlyph) smoothCaret.follow(smoothCaret.targetGlyph); });
                        }
                        Flickable {
                            id: passageVisuals
                            objectName: "typing-page-visuals"
                            readonly property real centerPadding: Math.max(4, (height - root.passageLineHeight) / 2)
                            contentHeight: passageFlow.height + 2 * centerPadding
                            onHeightChanged: Qt.callLater(root.refreshPageCaret)
                            contentWidth: width
                            boundsBehavior: Flickable.StopAtBounds
                            flickableDirection: Flickable.VerticalFlick
                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                            visible: !root.fullscreen
                            anchors.fill: parent
                            readonly property real pagePop: root.effectKind === "page" ? root.effectStrength : 0
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
                                y: passageVisuals.centerPadding
                                onYChanged: Qt.callLater(() => { if (smoothCaret.targetGlyph) smoothCaret.follow(smoothCaret.targetGlyph); })
                                z: 1
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.leftMargin: 4
                                anchors.rightMargin: 4
                                spacing: 0
                                Repeater {
                                    id: wordRepeater
                                    model: root.passageWords
                                    delegate: Row {
                                        id: word
                                        required property var modelData
                                        // Flow must wrap with the same widths used by pagination.
                                        // Row implicit widths can differ under native font hinting.
                                        // Keep lightweight word geometry for the whole section,
                                        // but build animated characters only near the viewport.
                                        height: root.passageLineHeight
                                        readonly property bool inRenderWindow: !root.fullscreen
                                            && modelData.line * root.passageLineHeight + passageFlow.y + height >= passageVisuals.contentY - root.passageLineHeight * 2
                                            && modelData.line * root.passageLineHeight + passageFlow.y <= passageVisuals.contentY + passageVisuals.height + root.passageLineHeight * 2
                                        readonly property var letters: root.characters(modelData.text)
                                        readonly property var offsets: {
                                            let offset = modelData.start;
                                            return letters.map(letter => { const start = offset; offset += letter.length; return start; });
                                        }
                                        width: letters.reduce((total, letter) => total + root.characterWidth(letter), 0)
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
                                            model: word.inRenderWindow ? word.letters : []
                                            delegate: StyledText {
                                                id: glyph
                                                required property int index
                                                required property string modelData
                                                property bool caretHere: false
                                                property bool typed: false
                                                property bool incorrect: false
                                                property bool initialized: false
                                                property string enteredCharacter: ""
                                                property bool failedFeedback: false
                                                property real spark: 0
                                                readonly property real rejectionPhase: 1 - Math.pow(Math.max(0, spark), 1 / 3)
                                                readonly property real rejectionOffset: failedFeedback ? Math.sin(rejectionPhase * Math.PI * 8) * spark * 8 : 0
                                                scale: 1 + spark * (failedFeedback ? 0.28 : 0.105)
                                                rotation: failedFeedback ? rejectionOffset * 1.6 : 0
                                                transform: Translate {
                                                    x: glyph.rejectionOffset
                                                    y: -glyph.spark * (glyph.failedFeedback ? 4 : 2.2)
                                                }
                                                transformOrigin: Item.Center
                                                function celebrate() { root.requestFeedback("letter", glyph); }
                                                function startFeedback(failed = false) { failedFeedback = failed; keyFeedback.restart(); }
                                                function stopFeedback() { keyFeedback.stop(); spark = 0; failedFeedback = false; root.forgetGlyph(glyph); }
                                                NumberAnimation {
                                                    id: keyFeedback
                                                    target: glyph
                                                    property: "spark"
                                                    from: 1
                                                    to: 0
                                                    duration: glyph.failedFeedback ? 560 : Math.max(280, Math.min(420, Motion.feedback * 2.4))
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
                                                    growth: glyph.failedFeedback ? 0.55 : 0.12
                                                    color: Qt.alpha(glyph.failedFeedback ? Colors.error : Colors.primary, glyph.failedFeedback ? 0.32 : 0.07)
                                                    border.color: Qt.alpha(glyph.failedFeedback ? Colors.error : Colors.primary, glyph.failedFeedback ? 0.9 : 0.22)
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
                                                    if (smoothCaret.targetGlyph === glyph) { smoothCaret.targetGlyph = null; smoothCaret.placed = false; }
                                                    if (root.glyphItems[characterIndex] === glyph) delete root.glyphItems[characterIndex];
                                                }
                                                onVisibleChanged: { if (!visible) stopFeedback(); else if (initialized && caretHere) Qt.callLater(() => smoothCaret.follow(glyph)); }
                                                readonly property int characterIndex: word.offsets[index]
                                                objectName: "typing-character-" + characterIndex
                                                text: modelData === " " ? "\u00a0" : modelData
                                                textFormat: Text.PlainText
                                                width: root.characterWidth(modelData)
                                                font: Qt.font({family: root.readingFont.family, pixelSize: root.readingFont.pixelSize, weight: Font.Normal, underline: glyph.incorrect})
                                                height: root.passageLineHeight
                                                lineHeight: 1.45
                                                property real inkOpacity: caretHere || typed ? 1 : (word?.modelData?.line === root.scrollLine ? 0.85 : 0.65)
                                                Behavior on inkOpacity {
                                                    enabled: Motion.enabled && glyph.initialized && !root.restoring && !root.busy
                                                    NumberAnimation { duration: 110; easing.type: Easing.OutCubic }
                                                }
                                                Behavior on color {
                                                    enabled: Motion.enabled && glyph.initialized && !root.restoring && !root.busy && !glyph.incorrect
                                                    ColorAnimation { duration: 130; easing.type: Easing.OutCubic }
                                                }
                                                opacity: caretHere ? 1 : inkOpacity

                                                color: typed && incorrect ? Qt.tint(Colors.error, Qt.alpha(Colors.overSurface, spark * 0.45)) : Qt.tint(Colors.overSurface, Qt.alpha(Colors.primary, Math.min(0.88, (typed ? 0.38 : 0) + spark * 0.50 + (word?.linePop ?? 0) * 0.12)))

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
                                    const point = item.parent.mapToItem(passageVisuals.contentItem, item.x, item.y);
                                    // Padding lets even the first and last rows stay centered.
                                    passageVisuals.contentY = Math.max(0, Math.min(
                                        passageVisuals.contentHeight - passageVisuals.height,
                                        point.y + root.passageLineHeight / 2 - passageVisuals.height / 2));
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
                            id: readerText
                            objectName: "reader-page-text"
                            opacity: 0.35 + 0.65 * root.readerReveal
                            transform: Translate {
                                x: (1 - root.readerReveal) * root.readerDirection * 12
                                y: (1 - root.readerReveal) * 3
                            }
                            anchors.fill: parent
                            anchors.margins: 4
                            visible: root.fullscreen
                            readOnly: true
                            selectByMouse: true
                            textFormat: TextEdit.RichText
                            text: root.readerHtml(root.passage)
                            font: root.readingFont
                            color: Colors.overSurface
                            selectionColor: Qt.alpha(Colors.primary, 0.3)
                            selectedTextColor: Colors.overSurface
                            wrapMode: TextEdit.Wrap
                            cursorVisible: false
                            Accessible.name: "Book passage"
                            TapHandler {
                                acceptedButtons: Qt.RightButton
                                onTapped: point => root.openWord(root.readingWordAt(readerText.positionAt(point.position.x, point.position.y)))
                            }
                            Keys.onPressed: event => { event.accepted = root.readerKey(event); }
                        }
                        TextEdit {
                            id: answer
                            visible: !root.fullscreen
                            readOnly: root.fullscreen || root.busy
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
                            WheelHandler {
                                onWheel: event => {
                                    passageVisuals.contentY = Math.max(0, Math.min(passageVisuals.contentHeight - passageVisuals.height,
                                        passageVisuals.contentY - event.angleDelta.y / 120 * root.passageLineHeight * 3));
                                    event.accepted = true;
                                }
                            }
                            font: root.readingFont
                            TapHandler { onTapped: { root.focusPassage(); answer.cursorPosition = answer.length; } }
                            TapHandler {
                                acceptedButtons: Qt.RightButton
                                onTapped: point => {
                                    for (let index = 0; index < wordRepeater.count; index++) {
                                        const wordItem = wordRepeater.itemAt(index);
                                        const local = wordItem.mapFromItem(answer, point.position.x, point.position.y);
                                        if (wordItem.contains(local)) { root.openWord(wordItem.modelData.text); break; }
                                    }
                                }
                            }
                            // The invisible editor only captures input; custom glyphs do the wrapping.
                            wrapMode: TextEdit.NoWrap
                            inputMethodHints: Qt.ImhNoPredictiveText
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
                    StyledRect {
                        objectName: "reader-keyboard-guide"
                        visible: root.fullscreen && root.readerHelp
                        Layout.fillWidth: true
                        implicitHeight: readerHelpText.implicitHeight + 24
                        variant: "pane"
                        radius: 12
                        StyledText {
                            id: readerHelpText
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 12
                            text: "Next: l / → / Page Down / Space   Previous: h / ← / Page Up / Shift+Space\nChapter: k / j or [ / ]   Notes: N   Word lookup: Ctrl+Space\nShortcut guide: ?   Exit reading: F11 or Esc"
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                        }
                    }
                    RowLayout {
                        visible: root.fullscreen
                        Layout.fillWidth: true
                        ReaderNavButton { objectName: "reader-previous-page"; text: "‹ Previous"; enabled: !root.busy && root.position > 0; onClicked: root.readPreviousPage() }
                        StyledText { text: Math.round(root.progress * 100) + "% read"; font.pixelSize: 12; opacity: 0.5; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                        TextButton { objectName: "reader-shortcut-help"; text: "?"; Accessible.name: "Keyboard shortcuts"; onClicked: root.readerHelp = !root.readerHelp }
                        ReaderNavButton { objectName: "reader-next-page"; text: root.position + root.characters(root.passage).length >= root.bookLength ? "End of book" : "Next ›"; enabled: !root.busy && root.position + root.characters(root.passage).length < root.bookLength; onClicked: root.readNextPage() }
                    }
                    RowLayout {
                        visible: !root.fullscreen || root.errorMessage.length > 0
                        Layout.fillWidth: true
                        StyledText { text: root.errorMessage || (root.busy ? "Loading…" : (!root.fullscreen && !answer.activeFocus ? "Click the passage to continue typing" : root.chapterTitle)); textFormat: Text.PlainText; color: root.errorMessage ? Colors.error : Colors.overSurface; opacity: root.errorMessage ? 1 : 0.7; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true; Layout.minimumWidth: 0 }
                        StyledText { objectName: "typing-live-wpm"; visible: !root.fullscreen; text: root.liveWpm + " WPM"; color: Colors.primary; font.pixelSize: 12 }
                        StyledText { text: (root.progress * 100).toFixed(1) + "%"; opacity: 0.5; font.pixelSize: 11 }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: root.fullscreen ? 1 : 2
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
