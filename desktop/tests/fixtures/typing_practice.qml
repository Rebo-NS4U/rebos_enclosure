import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.modules.bar.layouts
import qs.modules.shell
import "TypingSpeed.js" as Speed
import "TypingPaging.js" as Pages
import qs.modules.theme
ShellRoot {
    id: harness
    property bool closeRequested: false
    PanelWindow {
        id: testWindow
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
        exclusionMode: ExclusionMode.Ignore
        mask: Region {}
        implicitWidth: 640
        implicitHeight: 600
        color: "transparent"
        TypingMenu { id: practice; anchors.fill: parent; onBackRequested: harness.closeRequested = true }
        Loader { id: freshView; anchors.fill: parent; active: false; visible: false; sourceComponent: TypingMenu {} }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (let child of item.children ?? []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        property int phase: 0
        property int expectedPosition: 0
        property string expectedBuffered: ""
        interval: Math.max(900, Motion.base * 1.5)
        running: true
        repeat: true
        onTriggered: {
            try {
                if (phase === 0) {
                    for (const quote of "‘’‚‛'")
                        if (!Pages.matchingCharacter("'", quote)) throw Error("Single quote rejected");
                    for (const quote of '“”„‟"')
                        if (!Pages.matchingCharacter('"', quote)) throw Error("Double quote rejected");
                    for (const dash of "‐‑‒–—―-")
                        if (!Pages.matchingCharacter("-", dash)) throw Error("Keyboard hyphen rejected for book dash");
                    if (Pages.matchingCharacter("'", '"') || Pages.matchingCharacter("a", "A")) throw Error("Different characters accepted");
                    practice.restoring = true;
                    practice.pageSource = "“Don’t”—go–on";
                    practice.fitPage();
                    const quoteInput = find(practice, "typing-input");
                    quoteInput.text = "\"Don't\"-go-on";
                    if (practice.correctCount() !== 13) throw Error("Keyboard quotes must count toward accuracy and WPM");
                    find(practice, "typing-fullscreen").clicked();
                    if (!practice.fullscreen || practice.correctCount() !== 13 || quoteInput.text !== "\"Don't\"-go-on") throw Error("Fullscreen lost typed input");
                    practice.handleEscape();
                    if (practice.fullscreen || practice.correctCount() !== 13) throw Error("Escape did not restore compact typing");
                    quoteInput.text = "";
                    practice.restoring = false;
                    if (!Pages.prepareInput(".", "…").pending || !Pages.prepareInput("..", "…").pending) throw Error("Partial ellipsis must wait for three periods");
                    if (Pages.prepareInput("Wait... now...", "Wait… now…").text !== "Wait… now…") throw Error("Ellipsis composition failed");
                    if (Pages.prepareInput("...", "...").text !== "...") throw Error("Literal periods were changed");
                    if (Pages.prepareInput("…", "…").pending) throw Error("Direct ellipsis must remain supported");
                    const moreLines = Pages.layout("word ".repeat(500), 580, text => 13, 12);
                    if (moreLines.lines !== 12 || moreLines.text.length <= 90) throw Error("Fullscreen must show more than two lines");
                    let meter = Speed.record(Speed.create(), 1000);
                    meter = Speed.tick(meter, 2000, true);
                    if (Speed.rate(meter, 5, 2000) !== 60 || Speed.rate(meter, 0, 2000) !== 0) throw Error("WPM must count net correct five-character words");
                    const paused = Speed.pause(meter);
                    if (Speed.tick(paused, 9000, true).elapsed !== meter.elapsed || Speed.rate(meter, 5, 7000) !== 0) throw Error("WPM idle/pause handling failed");
                    const tiny = Pages.layout("abcdefghijkl", 30, text => 10, 0);
                    if (tiny.text !== "abcdef" || tiny.lines !== 2) throw Error("Two-line fitting failed");
                    const original = "😀 alpha beta gamma delta averylongwordwithoutspaces ".repeat(4);
                    const letters = Pages.characters(original);
                    let consumed = 0, rebuilt = "";
                    while (consumed < letters.length) {
                        const page = Pages.layout(letters.slice(consumed, consumed + 90).join(""), 100, text => 10, 0);
                        if (!page.text.length || page.lines > 2) throw Error("Page fitting stalled or used a third line");
                        rebuilt += page.text; consumed += Pages.characters(page.text).length;
                    }
                    if (rebuilt !== original) throw Error("Paging dropped or duplicated book characters");
                    const bar = Qt.createComponent("modules/bar/layouts/IslandBar.qml");
                    if (bar.status === Component.Error) throw Error(bar.errorString());
                    const island = bar.createObject(testWindow.contentItem, {screen: testWindow.screen, visible: false});
                    if (!island) throw Error("Could not create island for fullscreen check");
                    island.currentMode = "typing";
                    const compactWidth = island.targetWidth;
                    const typingContainer = find(island, "typing-island-container");
                    if (typingContainer.y !== island.containerY) throw Error("Compact typer must remain at the top");
                    island.typingPractice.toggleFullscreen();
                    if (!island.typingFullscreen || island.targetWidth !== Math.min(960, island.width - 64) || island.targetHeight !== island.height) throw Error("Fullscreen reading width or height is incorrect");
                    if (typingContainer.y !== Math.max(0, (island.height - typingContainer.height) / 2)) throw Error("Fullscreen must remain vertically centered");
                    island.typingPractice.handleEscape();
                    if (island.typingFullscreen || island.targetWidth !== compactWidth || typingContainer.y !== island.containerY) throw Error("Compact dimensions were not restored");
                    island.destroy();
                    const panel = Qt.createComponent("modules/shell/UnifiedShellPanel.qml");
                    if (panel.status === Component.Error) throw Error(panel.errorString());
                    practice.loadPreset(0); practice.start(); phase++; return;
                }
                if (practice.busy || !practice.passage.length) return;
                if (practice.practicing && (practice.pageLayout.lines > practice.pageLineLimit || practice.implicitHeight !== 240)) throw Error("Practice is not compact");
                const input = find(practice, "typing-input");
                const first = find(practice, "typing-character-0");
                if (!input || !first) throw Error("Typing input or glyph missing");
                if (input.opacity !== 0 || !input.enabled) throw Error("Native editor must accept input without painting ghost characters");
                if (phase === 1) {
                    const originalSource = practice.pageSource;
                    const screenshotText = "comfortable? I have a better view of things now. This is no ordinary hospital room. More words follow here.";
                    practice.pageSource = screenshotText; practice.fitPage();
                    find(practice, "typing-passage-flow").forceLayout();
                    const screenshotPage = practice.passage;
                    const screenshotPosition = practice.position;
                    input.text = screenshotText.slice(0, 68); input.cursorPosition = 68;
                    const spaceCaret = find(practice, "typing-smooth-caret");
                    spaceCaret.follow(find(practice, "typing-character-68"));
                    if (!find(practice, "typing-space-indicator").visible || spaceCaret.targetGlyph.modelData !== " ") throw Error("Cursor must identify the space before the final word");
                    input.insert(input.cursorPosition, " ");
                    if (practice.busy || practice.position !== screenshotPosition || practice.passage !== screenshotPage) throw Error("Typing the space before the last word turned the page early");
                    input.text = "";
                    practice.fullscreen = true;
                    practice.pageSource = "word ".repeat(800); practice.fitPage();
                    if (practice.pageLayout.lines <= 2) throw Error("Fullscreen must show additional lines");
                    const editStarted = Date.now();
                    for (let count = 1; count <= 120; count++) input.text = practice.passage.slice(0, count);
                    console.log("Fullscreen 120 input updates: " + (Date.now() - editStarted) + " ms");
                    const editedGlyph = find(practice, "typing-character-10");
                    const originalTyped = input.text;
                    input.text = originalTyped.slice(0, 10) + "!" + originalTyped.slice(11);
                    if (!editedGlyph.incorrect) throw Error("Middle edit did not update error state");
                    input.text = originalTyped;
                    if (editedGlyph.incorrect) throw Error("Correction did not clear error state");
                    find(practice, "typing-passage-flow").forceLayout();
                    const movingCaret = find(practice, "typing-smooth-caret");
                    const activeLine = find(practice, "typing-line-highlight");
                    input.cursorPosition = input.length;
                    movingCaret.follow(find(practice, "typing-character-120"));
                    if (movingCaret.targetRowY <= 0 || activeLine.y !== movingCaret.rowY) throw Error("Line highlight did not follow wrapped text");
                    input.cursorPosition = 0;
                    movingCaret.follow(find(practice, "typing-character-0"));
                    const firstRowGlyph = find(practice, "typing-character-0");
                    const firstRowPoint = firstRowGlyph.parent.mapToItem(movingCaret.parent, firstRowGlyph.x, firstRowGlyph.y);
                    if (Math.abs(movingCaret.targetRowY - Math.max(0, firstRowPoint.y + firstRowGlyph.baselineOffset + practice.highlightBounds.y - practice.highlightPadding)) > 0.01) throw Error("Line highlight did not return to the centered first line");
                    input.text = "";
                    if (editedGlyph.typed) throw Error("Backspace did not clear typed state");
                    practice.fullscreen = false;
                    practice.pageSource = "… next"; practice.fitPage();
                    input.text = ".";
                    if (practice.turningPage) throw Error("First ellipsis period advanced the page");
                    input.text = "..";
                    if (practice.turningPage) throw Error("Second ellipsis period advanced the page");
                    input.text = "...";
                    if (input.text !== "…" || practice.correctCount() !== 1) throw Error("Three periods did not compose in the input field");
                    input.text = ""; practice.pageSource = originalSource; practice.fitPage();
                    const caret = find(practice, "typing-smooth-caret");
                    const core = find(practice, "typing-caret-core");
                    if (find(practice, "typing-caret-0")) throw Error("Letter underline must not be rendered");
                    const line = find(practice, "typing-line-highlight");
                    if (line.border.width !== 0 || line.children.length !== 0) throw Error("Line highlight must have uniform transparency without a side strip");
                    const textFlow = find(practice, "typing-passage-flow");
                    if (Math.abs(textFlow.y + textFlow.height / 2 - textFlow.parent.height / 2) > 1) throw Error("Passage is not vertically centered");
                    const centeredWord = find(practice, "typing-character-0").parent;
                    if (Math.abs(centeredWord.centerOffset - (textFlow.width - practice.pageLayout.lineWidths[0]) / 2) > 1) throw Error("Text line is not horizontally centered");
                    if (!line.visible || line.width < practice.width - 60 || line.height < 25 || line.y !== caret.rowY) throw Error("Current line highlight is missing or too narrow");
                    if (caret.accent.toString() !== Colors.primary.toString()) throw Error("Cursor must use the exact theme accent");
                    if (first.style !== Text.Normal || first.color.toString() !== Colors.overSurface.toString()) throw Error("Text must use the normal theme color without outlines");
                    if (!caret.visible || core.width < 12 || core.height < 20 || core.radius < 4 || core.color.a < 0.35) throw Error("Rounded glass cursor is missing or too faint");
                    if (!find(practice, "typing-character-0").caretHere || Math.abs(first.opacity - 1) > 0.001) throw Error("Current-character highlight missing: " + JSON.stringify({opacity: first.opacity, current: first.caretHere, entrance: first.entrance, cursor: input.cursorPosition, practicing: practice.practicing, visible: find(practice, "typing-character-0").caretHere, motion: Motion.base}));
                    if (Math.abs(find(practice, "typing-character-1").opacity - 0.65) > 0.001) throw Error("Upcoming text must remain readable");
                    input.text = practice.passage[0]; input.cursorPosition = input.length;
                } else if (phase === 2) {
                    if (Math.abs(first.opacity - 1) > 0.001) throw Error("Typed glyph did not become opaque after animation");
                    const settled = find(practice, "typing-smooth-caret");
                    const settledLine = find(practice, "typing-line-highlight");
                    const activeGlyph = settled.targetGlyph;
                    const baseline = activeGlyph.parent.mapToItem(settled.parent, activeGlyph.x, activeGlyph.y).y + activeGlyph.baselineOffset;
                    const inkTop = baseline + practice.highlightBounds.y;
                    const topPadding = inkTop - settled.y;
                    const bottomPadding = settled.y + settled.height - (inkTop + practice.highlightBounds.height);
                    if (Math.abs(topPadding - bottomPadding) > 0.01 || Math.abs(topPadding - practice.highlightPadding) > 0.01) throw Error("Highlight does not have equal top and bottom padding");
                    if (Math.abs(settled.y - settledLine.y) > 0.01 || Math.abs(settled.height - settledLine.height) > 0.01) throw Error("Cursor and line boxes must share vertical bounds");
                    if (Math.abs(settled.x - settled.targetX) > 0.01 || Math.abs(settled.y - settled.targetY) > 0.01 || Math.abs(settledLine.y - settled.targetRowY) > 0.01) throw Error("Cursor and line transitions did not settle together");
                    if (!find(practice, "typing-character-1").caretHere || find(practice, "typing-smooth-caret").targetGlyph.characterIndex !== 1) throw Error("Cursor did not advance");
                    input.cursorPosition = 0;
                    if (!find(practice, "typing-character-0").caretHere) throw Error("Cursor does not follow editing position");
                    practice.openBook(practice.bookId);
                } else if (phase === 3) {
                    if (input.text !== practice.passage[0]) throw Error("Partial typing progress did not resume");
                    input.text = "";
                } else if (phase < 100) {
                    if (phase === 4 && (!find(practice, "typing-character-0").caretHere || Math.abs(find(practice, "typing-character-1").opacity - 0.65) > 0.001)) throw Error("Backspace did not restore the cursor and readable upcoming text");
                    const pageCaret = find(practice, "typing-smooth-caret");
                    const firstGlyph = find(practice, "typing-character-0");
                    const firstPoint = firstGlyph.parent.mapToItem(pageCaret.parent, firstGlyph.x, firstGlyph.y);
                    const expectedRow = Math.max(0, firstPoint.y + firstGlyph.baselineOffset + practice.highlightBounds.y - practice.highlightPadding);
                    if (pageCaret.targetGlyph !== firstGlyph || Math.abs(pageCaret.targetRowY - expectedRow) > 0.01) throw Error("New page did not reset the highlight to its first row: " + JSON.stringify({phase: phase, position: practice.position, targetCorrect: pageCaret.targetGlyph === firstGlyph, row: pageCaret.targetRowY, expected: expectedRow, cursor: input.cursorPosition}));
                    if (practice.rounds < 1) {
                        const stablePage = practice.passage;
                        const stablePosition = practice.position;
                        const pageLetters = practice.characters(stablePage);
                        for (let count = 1; count < pageLetters.length; count++) {
                            input.text = pageLetters.slice(0, count).join(""); input.cursorPosition = input.length;
                            if (practice.busy || practice.position !== stablePosition || practice.passage !== stablePage) throw Error("Passage changed before its final character was entered");
                        }
                        pageCaret.follow(find(practice, "typing-character-" + input.cursorPosition));
                        input.text = practice.passage; phase++; return;
                    }
                    if (practice.position !== 0) throw Error("Continuous loop failed");
                    phase = 100;
                    practice.send({action: "add", title: "Unicode test", text: "😀 A gentle morning with words to type. ".repeat(8) + "\nChapter Two\nA new chapter begins here."});
                    return;
                } else if (phase === 100) {
                    if (first.text !== "😀") throw Error("Unicode glyph was split");
                    expectedPosition = practice.characters(practice.passage).length;
                    expectedBuffered = Pages.characters(practice.pageSource.slice(practice.passage.length))[0] || "";
                    input.text = practice.passage;
                    if (!practice.turningPage) throw Error("Completing the second line did not start the next page");
                    practice.queueTyping(expectedBuffered + "?");
                    practice.undoQueuedKey();
                } else if (phase === 101) {
                    if (practice.position !== expectedPosition) throw Error("Unicode book position drifted");
                    if (input.text !== expectedBuffered) throw Error("Typing during page turn was lost or duplicated");
                    if (practice.library.length < 2) throw Error("Library did not retain books");
                    practice.showLibrary();
                    const chapters = find(practice, "typing-chapter-select");
                    if (chapters.currentIndex !== practice.currentChapterIndex || !chapters.displayText.length) throw Error("Chapter selection is not synchronized");
                    chapters.popup.open();
                } else if (phase === 102) {
                    const cards = find(practice, "typing-book-cards");
                    const card = cards.itemAtIndex(0);
                    if (!card || cards.count !== 1 || !find(card, "typing-card-progress").text.endsWith("%")) throw Error("Book cards invalid: " + JSON.stringify({count: cards.count, visible: cards.visible, height: cards.height, card: !!card, books: practice.libraryBooks.length, viewWidth: practice.width, viewHeight: practice.height, parentHeight: cards.parent.height, samples: practice.samplesExpanded}));
                    if (practice.samplesExpanded) throw Error("Practice samples should be collapsed by default");
                    const chapters = find(practice, "typing-chapter-select");
                    chapters.popup.contentItem.positionViewAtIndex(1, ListView.Contain);
                    const entry = chapters.popup.contentItem.itemAtIndex(1);
                    if (!entry || entry.text !== "Chapter Two") throw Error("Chapter popup is missing its labels");
                    entry.clicked();
                    phase = 110; return;
                } else if (phase === 110) {
                    if (practice.chapterTitle !== "Chapter Two" || !practice.passage.startsWith("Chapter Two") || !practice.practicing) throw Error("Chapter selection did not jump back to typing");
                    const slider = find(practice, "typing-book-position");
                    slider.value = Math.floor(practice.bookLength / 2);
                    slider.moved();
                    phase = 103; return;
                } else if (phase === 103) {
                    if (practice.progress < 0.45 || practice.progress > 0.65) throw Error("Book position slider failed");
                    const place = practice.position;
                    find(practice, "typing-library").clicked();
                    if (practice.practicing) throw Error("Library button did not open library");
                    find(practice, "typing-back").clicked();
                    if (!practice.practicing || practice.position !== place || harness.closeRequested) throw Error("Back left typing or lost the current passage");
                    find(practice, "typing-library").clicked();
                    find(practice, "typing-import").clicked();
                } else if (phase === 104) {
                    if (!practice.filePickerActive) throw Error("File picker did not release panel input");
                } else if (phase === 105) {
                    if (practice.filePickerActive || practice.busy) return;
                    if (practice.bookTitle !== "picker test book" || practice.chapters.length !== 1) throw Error("Picker did not import the EPUB");
                    find(practice, "typing-back").clicked();
                    if (!practice.practicing || harness.closeRequested) throw Error("Back did not return to imported EPUB typing");
                    practice.openImport();
                } else if (phase === 106) {
                    if (!practice.filePickerActive) throw Error("Second picker did not open");
                } else if (phase === 107) {
                    if (practice.filePickerActive || practice.busy) return;
                    if (practice.bookTitle !== "picker test book") throw Error("Cancelling the picker changed the current book");
                    practice.goBack();
                    if (!practice.practicing || harness.closeRequested) throw Error("Back failed after cancelling the picker");
                    input.text = practice.passage.slice(0, 3);
                    input.cursorPosition = input.length;
                    practice.saveProgress();
                    practice.visible = false;
                    freshView.active = true;
                    freshView.visible = true;
                    freshView.item.reopen();
                } else if (phase === 108) {
                    const restored = freshView.item;
                    if (restored.busy || !restored.bookId || restored.library.length < 3) return;
                    const restoredInput = find(restored, "typing-input");
                    if (!restored.practicing || restored.bookTitle !== "picker test book" || restoredInput.text !== restored.passage.slice(0, 3)) throw Error("A fresh view did not automatically resume the saved partial passage");
                    if (restored.libraryBooks.length !== 2 || restored.liveWpm !== 0) throw Error("Practice samples or restored text affect library/WPM");
                    const legacy = restored.library.find(book => book.title === "Unicode test");
                    restored.send({action: "seek", id: legacy.id, position: 0, typed: "x".repeat(85), loops: 0});
                    phase = 111; return;
                } else if (phase === 111) {
                    const restored = freshView.item;
                    if (restored.busy) return;
                    const field = find(restored, "typing-input");
                    if (restored.pageLayout.lines > 2 || restored.position + restored.characters(field.text).length !== 85 || restored.liveWpm !== 0) throw Error("Legacy page carryover lost saved input or counted it as WPM");
                    expectedPosition = restored.position + restored.characters(restored.passage).length;
                    field.text = "z".repeat(restored.characters(restored.passage).length);
                    if (!restored.turningPage) throw Error("Typos blocked continuous page advance");
                } else if (phase === 112) {
                    const restored = freshView.item;
                    if (restored.busy) return;
                    if (restored.position !== expectedPosition || restored.pageLayout.lines > 2) throw Error("Continuous two-line advance failed");
                    console.log("PASS: two-line fitting, lossless paging, queued input, legacy bookmark carryover, no-fail advance, resume, WPM and EPUB import");
                    Qt.quit();
                }

                phase++;
            } catch (error) { console.error(error); Qt.quit(); }
        }
    }
}
