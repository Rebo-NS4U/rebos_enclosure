import QtQuick
import QtTest as TestTools
import Quickshell
import Quickshell.Wayland
import qs.modules.bar.layouts
import qs.modules.shell
import "TypingSpeed.js" as Speed
import "TypingPaging.js" as Pages
import qs.modules.theme
import qs.config
ShellRoot {
    id: harness
    property bool closeRequested: false
    PanelWindow {
        id: testWindow
        TestTools.TestCase { id: keyDriver; name: "TypingKeystrokes"; when: false }
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
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
        if (item.readerMenu) {
            const found = find(item.readerMenu.contentItem, name);
            if (found) return found;
        }
        if (item.wordTools) {
            if (item.wordTools.objectName === name) return item.wordTools;
            const found = find(item.wordTools.contentItem, name);
            if (found) return found;
        }
        for (let child of item.children ?? []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        property bool stepping: false
        property bool backTested: false
        property int phase: 0
        property int expectedPosition: 0
        property string expectedBuffered: ""
        interval: Math.max(900, Motion.base * 1.5)
        running: true
        repeat: true
        onTriggered: {
            if (stepping) return;
            stepping = true;
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
                    find(practice, "typing-reader-actions").clicked();
                    if (!practice.readerMenu.opened || !find(practice, "typing-fullscreen")) throw Error("Reader actions menu did not expose fullscreen");
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
                    practice.samplesExpanded = true;
                    find(practice, "typing-sample-select").activated(0); phase++; return;
                }
                if (practice.busy || !practice.passage.length) return;
                if (practice.practicing && (practice.pageLayout.lines > practice.pageLineLimit || practice.implicitHeight !== 116 + 4 * practice.passageLineHeight)) throw Error("Practice is not compact");
                const input = find(practice, "typing-input");
                let first = find(practice, "typing-character-0");
                if (!input || !first) throw Error("Typing input or glyph missing");
                if (input.opacity !== 0 || !input.enabled) throw Error("Native editor must accept input without painting ghost characters");
                if (phase === 1) {
                    if (!practice.practicing || practice.draft || !input.activeFocus) throw Error("Selecting a sample must open focused typing without Start practice");
                    input.forceActiveFocus();
                    practice.speedState = {elapsed: 1000, lastTick: Date.now(), lastInput: Date.now()};
                    practice.forceActiveFocus();
                    if (practice.speedState.lastInput !== 0 || practice.speedState.elapsed < 1000) throw Error("Focus loss did not pause the speed clock");
                    if (find(practice, "typing-smooth-caret").opacity >= 1) throw Error("Inactive caret must dim");
                    input.forceActiveFocus();
                    if (find(practice, "typing-smooth-caret").opacity !== 1) throw Error("Active caret must regain emphasis");
                    const originalSource = practice.pageSource;
                    practice.pageSource = "word ".repeat(800); practice.fitPage();
                    if (practice.pageLineLimit !== Math.max(1, Math.floor(Math.max(0, find(practice, "typing-passage-flow").parent.height - 8) / practice.passageLineHeight)) || practice.pageLayout.lines !== practice.pageLineLimit) throw Error("Practice must fill the available height with complete lines");
                    const filledFlow = find(practice, "typing-passage-flow");
                    filledFlow.forceLayout();
                    if (filledFlow.parent.height - filledFlow.height >= practice.passageLineHeight + 8) throw Error("Long passage leaves an empty row");
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
                    practice.fullscreen = false;
                    practice.pageSource = "word ".repeat(800); practice.fitPage();
                    if (practice.pageLayout.lines <= 2) throw Error("Tall typing view must show additional lines");
                    const editStarted = Date.now();
                    for (let count = 1; count <= 120; count++) input.text = practice.passage.slice(0, count);
                    console.log("Typing 120 input updates: " + (Date.now() - editStarted) + " ms");
                    const editedGlyph = find(practice, "typing-character-10");
                    const originalTyped = input.text;
                    input.text = originalTyped.slice(0, 10) + "!" + originalTyped.slice(11);
                    if (!editedGlyph.incorrect || !editedGlyph.font.underline) throw Error("Middle edit did not underline the mistake");
                    if (Motion.enabled) {
                        if (!editedGlyph.failedFeedback || editedGlyph.spark <= 0 || editedGlyph.scale <= 1.2) throw Error("Mistype did not trigger exaggerated feedback");
                        const failures = practice.failureEvents;
                        practice.syncGlyphs(); practice.syncCaret();
                        if (practice.failureEvents !== failures) throw Error("Caret refresh replayed failure feedback");
                        keyDriver.wait(50);
                        if (Math.abs(editedGlyph.rejectionOffset) < 0.1) throw Error("Mistyped letter did not shake");
                        input.text = originalTyped.slice(0, 10) + "?" + originalTyped.slice(11);
                        if (practice.failureEvents !== failures + 1) throw Error("Another wrong input did not retrigger failure feedback");
                    }
                    input.text = originalTyped;
                    if (editedGlyph.incorrect || editedGlyph.font.underline || editedGlyph.failedFeedback) throw Error("Correction did not clear the error feedback");
                    const spaceIndex = originalTyped.indexOf(" ");
                    const wrongSpace = find(practice, "typing-character-" + spaceIndex);
                    input.text = originalTyped.slice(0, spaceIndex) + "!" + originalTyped.slice(spaceIndex + 1);
                    if (Motion.enabled && !wrongSpace.failedFeedback) throw Error("Mistyped space has no failure reaction");
                    input.text = originalTyped;
                    if (wrongSpace.failedFeedback || wrongSpace.incorrect || wrongSpace.spark !== 0) throw Error("Corrected space kept its failure reaction");
                    find(practice, "typing-passage-flow").forceLayout();
                    const movingCaret = find(practice, "typing-smooth-caret");
                    const activeLine = find(practice, "typing-line-highlight");
                    input.cursorPosition = 0;
                    movingCaret.follow(find(practice, "typing-character-0"));
                    const lineEvents = practice.lineTransitions;
                    input.cursorPosition = input.length;
                    movingCaret.follow(find(practice, "typing-character-120"));
                    if (Motion.enabled && practice.lineTransitions <= lineEvents) throw Error("Moving to a new line did not trigger the ripple");
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
                    input.forceActiveFocus();
                    keyDriver.keyClick(Qt.Key_Period, Qt.NoModifier, 0);
                    if (practice.turningPage) throw Error("First ellipsis period advanced the page");
                    if (practice.renderedCaret !== 0 || practice.displayedInput !== "") throw Error("First period moved the highlight past the ellipsis");
                    keyDriver.keyClick(Qt.Key_Period, Qt.NoModifier, 0);
                    if (practice.turningPage) throw Error("Second ellipsis period advanced the page");
                    if (practice.renderedCaret !== 0 || practice.displayedInput !== "") throw Error("Second period affected following letters");
                    keyDriver.keyClick(Qt.Key_Period, Qt.NoModifier, 0);
                    keyDriver.wait(0);
                    if (input.text !== "…" || practice.correctCount() !== 1) throw Error("Three periods did not compose in the input field: " + JSON.stringify({text: input.text, cursor: input.cursorPosition}));
                    if (input.cursorPosition !== 1) throw Error("Ellipsis moved the insertion point behind the composed character: " + input.cursorPosition);
                    keyDriver.keyClick(Qt.Key_Space, Qt.NoModifier, 0);
                    keyDriver.keyClick(Qt.Key_N, Qt.NoModifier, 0);
                    if (input.text !== "… n") throw Error("Typing after ellipsis shifted the following letters: " + input.text);
                    const prefix = "word ".repeat(26);
                    practice.pageSource = prefix + "… next"; practice.fitPage();
                    practice.restoring = true;
                    input.text = prefix + ".. next"; input.cursorPosition = prefix.length + 2;
                    practice.restoring = false;
                    keyDriver.keyClick(Qt.Key_Period, Qt.NoModifier, 0);
                    keyDriver.wait(0);
                    if (input.cursorPosition !== prefix.length + 1) throw Error("Composing an ellipsis in the last line moved the cursor into following text: " + input.cursorPosition + " expected " + (prefix.length + 1));
                    keyDriver.keyClick(Qt.Key_X, Qt.NoModifier, 0);
                    if (input.text !== prefix + "…x next") throw Error("Ellipsis editing corrupted following letters: " + JSON.stringify({text: input.text.slice(prefix.length), cursor: input.cursorPosition}));
                    input.text = ""; practice.pageSource = originalSource; practice.fitPage();
                    find(practice, "typing-passage-flow").forceLayout();
                    practice.refreshPageCaret();
                    first = find(practice, "typing-character-0");
                    const caret = find(practice, "typing-smooth-caret");
                    const core = find(practice, "typing-caret-core");
                    if (find(practice, "typing-caret-0")) throw Error("Letter underline must not be rendered");
                    const line = find(practice, "typing-line-highlight");
                    if (line.border.width !== 0 || line.children.length !== 0) throw Error("Line highlight must have uniform transparency without a side strip");
                    const textFlow = find(practice, "typing-passage-flow");
                    if (textFlow.y !== 4 || textFlow.height > textFlow.parent.height - 4) throw Error("Passage leaves unused rows or clips vertically");
                    for (const word of textFlow.children) {
                        if (!word.modelData || word.modelData.line === undefined) continue;
                        if (Math.abs(word.y - word.modelData.line * practice.passageLineHeight) > 1)
                            throw Error("Rendered wrapping disagrees with pagination");
                        if (word.x + word.centerOffset < -1 || word.x + word.centerOffset + word.width > textFlow.width + 1)
                            throw Error("Centered word extends outside the passage");
                    }
                    const centeredWord = find(practice, "typing-character-0").parent;
                    if (Math.abs(centeredWord.centerOffset - (textFlow.width - practice.pageLayout.lineWidths[0]) / 2) > 1) throw Error("Text line is not horizontally centered");
                    if (!line.visible || line.width < practice.width - 60 || line.height < practice.highlightBounds.height + 2 * practice.highlightPadding || line.y !== caret.rowY) throw Error("Current line highlight is missing or too narrow");
                    if (caret.accent.toString() !== Colors.primary.toString()) throw Error("Cursor must use the exact theme accent");
                    if (first.style !== Text.Normal || first.color.toString() !== Colors.overSurface.toString()) throw Error("Text must use the normal theme color without outlines");
                    if (first.font.family !== Config.theme.font || first.font.pixelSize !== Config.theme.fontSize + 2) throw Error("Passage must use the theme font with the larger reading size");
                    if (Math.abs(caret.width - caret.targetGlyph.width - 2 * practice.letterPadding) > 0.01) throw Error("Letter highlight is wider than a single character");
                    if (!caret.visible || core.width <= 0 || core.height <= 0 || core.radius <= 0 || core.color.a < 0.35) throw Error("Rounded glass cursor is missing or too faint");
                    if (!find(practice, "typing-character-0").caretHere || Math.abs(first.opacity - 1) > 0.001) throw Error("Current-character highlight missing: " + JSON.stringify({opacity: first.opacity, current: first.caretHere, cursor: input.cursorPosition, practicing: practice.practicing, visible: find(practice, "typing-character-0").caretHere, motion: Motion.base}));
                    if (Math.abs(find(practice, "typing-character-1").opacity - 0.65) > 0.001) throw Error("Upcoming text must remain readable");
                    input.forceActiveFocus();
                    const feedbackBefore = practice.feedbackEvents;
                    input.text = practice.passage[0]; input.cursorPosition = input.length;
                    keyDriver.wait(20);
                    if (Motion.enabled && (practice.feedbackEvents <= feedbackBefore || first.spark <= 0 || first.scale <= 1 || !find(first, "typing-key-halo-0").visible)) throw Error("Correct typing did not visibly trigger the pop and halo");
                    if (Motion.enabled) {
                        const nextGlyph = find(practice, "typing-character-1");
                        input.text = practice.passage.slice(0, 2); input.cursorPosition = input.length;
                        keyDriver.wait(20);
                        if (first.spark <= 0) throw Error("The next key canceled the previous letter fade");
                        if (nextGlyph.modelData.trim().length && nextGlyph.spark <= 0) throw Error("The next letter has no independent feedback");
                        const glide = find(practice, "typing-smooth-caret");
                        if (glide.glideAllowed && Math.abs(glide.x - glide.targetX) < 0.01) throw Error("Caret snapped instead of gliding between letters");
                        input.text = practice.passage[0]; input.cursorPosition = input.length;
                    }
                } else if (phase === 2) {
                    if (practice.activeEffects) return;
                    if (first.color.toString() === Colors.overSurface.toString()) throw Error("Completed letters lost their accent color");
                    if (Math.abs(first.parent.opacity - 1) > 0.001 || Math.abs(first.opacity - 1) > 0.001 || Math.abs(first.scale - 1) > 0.001) throw Error("Typed glyph did not settle after animation: " + JSON.stringify({opacity:first.opacity, scale:first.scale, spark:first.spark, strength:practice.effectStrength, kind:practice.effectKind, running:practice.activeEffects}));
                    if (Motion.enabled) {
                        practice.requestFeedback("letter", first);
                        practice.requestFeedback("line", first);
                        const burst = find(practice, "typing-transition-burst");
                        if (!burst.visible || burst.page || !find(practice, "typing-line-sweep").visible) throw Error("Line ribbon and spark burst missing");
                        practice.requestFeedback("letter", first);
                        if (practice.effectKind !== "line" || practice.activeEffects !== 2 || first.spark <= 0) throw Error("Line transition suppressed per-letter feedback");
                        practice.requestFeedback("page");
                        if (practice.effectKind !== "page" || practice.activeEffects !== 1 || find(practice, "typing-line-ripple").strength !== 0) throw Error("Page feedback overlapped the line pop");
                        keyDriver.wait(20);
                        if (!burst.visible || !burst.page || first.parent.arrival <= 0) throw Error("Page burst and staggered entrance missing");
                        const pageVisuals = find(practice, "typing-page-visuals");
                        if (pageVisuals.rotation !== 0 || pageVisuals.transform[0].yScale === pageVisuals.transform[0].xScale) throw Error("Page arrival did not use the squash-and-stretch effect");
                        practice.stopFeedback();
                        if (Math.abs(pageVisuals.transform[0].yScale - 1) > 0.001 || pageVisuals.opacity !== 1) throw Error("Page stretch did not reset cleanly");
                        if (burst.visible || first.parent.arrival !== 0 || first.parent.wave !== 0) throw Error("Transition visuals did not reset");
                        if (practice.activeEffects !== 0 || practice.effectStrength !== 0) throw Error("Feedback did not stop cleanly");
                    }
                    keyDriver.wait(140); // Let the short caret glide settle after the row transforms.
                    const settled = find(practice, "typing-smooth-caret");
                    const settledLine = find(practice, "typing-line-highlight");
                    const activeGlyph = settled.targetGlyph;
                    const baseline = activeGlyph.parent.mapToItem(settled.parent, activeGlyph.x, activeGlyph.y).y + activeGlyph.baselineOffset;
                    const inkTop = baseline + practice.highlightBounds.y;
                    const topPadding = inkTop - settled.y;
                    const bottomPadding = settled.y + settled.height - (inkTop + practice.highlightBounds.height);
                    if (Math.abs(topPadding - bottomPadding) > 0.01 || Math.abs(topPadding - practice.letterPadding) > 0.01) throw Error("Highlight does not have equal top and bottom padding");
                    if (Math.abs(settled.y + settled.height / 2 - settledLine.y - settledLine.height / 2) > 0.01) throw Error("Cursor and line boxes must share their vertical center");
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
                    keyDriver.wait(0); // Flush the animated row transform and caret anchor together.
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
                    practice.send({action: "add", title: "Unicode test", text: "😀 A gentle morning with words to type. ".repeat(80) + "\nChapter Two\nA new chapter begins here."});
                    return;
                } else if (phase === 100) {
                    if (first.text !== "😀") throw Error("Unicode glyph was split");
                    expectedPosition = practice.characters(practice.passage).length;
                    expectedBuffered = Pages.characters(practice.pageSource.slice(practice.passage.length))[0] || "";
                    input.text = practice.passage;
                    if (!practice.turningPage) throw Error("Completing the second line did not start the next page");
                    practice.queueTyping(expectedBuffered + "?");
                    practice.undoQueuedKey();
                } else if (phase === 130) {
                    if (practice.position !== 0 || practice.characters(input.text).length !== expectedPosition - 1) throw Error("Backspace did not restore the exact previous Unicode page");
                    keyDriver.keyClick(Qt.Key_Backspace, Qt.NoModifier, 0);
                    if (practice.characters(input.text).length !== expectedPosition - 2) throw Error("Backspace inside the restored page did not delete normally");
                    input.text = practice.passage;
                    keyDriver.keyClick(Qt.Key_Backspace, Qt.NoModifier, 0);
                } else if (phase === 131) {
                    if (practice.position !== 0 || practice.characters(input.text).length !== expectedPosition - 1) throw Error("Backspace during a page turn was lost");
                    input.text = practice.passage;
                    phase = 134; return;
                } else if (phase === 134) {
                    if (practice.position !== expectedPosition || input.text.length) throw Error("Correcting the previous page did not advance normally");
                    practice.pageHistory = [];
                    keyDriver.keyClick(Qt.Key_Backspace, Qt.NoModifier, 0);
                    phase = 132; return;
                } else if (phase === 132) {
                    if (practice.position >= expectedPosition || practice.position + practice.characters(input.text).length !== expectedPosition - 1) throw Error("Previous page without in-memory history lost its bookmark");
                    practice.send({action: "next", id: practice.bookId, position: expectedPosition, typed: expectedBuffered, loops: 0});
                } else if (phase === 133) {
                    backTested = true; phase = 101; return;
                } else if (phase === 101) {
                    if (!backTested) {
                        input.text = "";
                        input.forceActiveFocus();
                        keyDriver.keyClick(Qt.Key_Backspace, Qt.NoModifier, 0);
                        phase = 130; return;
                    }
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
                    const chapterCard = find(practice, "typing-chapter-card");
                    if (!chapterCard.visible || find(practice, "typing-chapter-card-title").text !== "Chapter Two" || chapterCard.height < 60) throw Error("Chapter jump did not show a prominent title card");
                    const slider = find(practice, "typing-book-position");
                    slider.value = Math.floor(practice.bookLength / 2);
                    slider.moved();
                    phase = 103; return;
                } else if (phase === 103) {
                    if (practice.progress < 0.45 || practice.progress > 0.65) throw Error("Book position slider failed");
                    if (find(practice, "typing-chapter-card").visible) throw Error("Chapter card stayed visible away from chapter start");
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
                    if (restored.pageLayout.lines > restored.pageLineLimit || restored.position + restored.characters(field.text).length !== 85 || restored.liveWpm !== 0) throw Error("Legacy page carryover lost saved input or counted it as WPM");
                    expectedPosition = restored.position + restored.characters(restored.passage).length;
                    field.text = "z".repeat(restored.characters(restored.passage).length);
                    if (!restored.turningPage) throw Error("Typos blocked continuous page advance");
                } else if (phase === 112) {
                    const restored = freshView.item;
                    if (restored.busy) return;
                    if (restored.position !== expectedPosition || restored.pageLayout.lines > restored.pageLineLimit) throw Error("Continuous available-height advance failed");
                    restored.send({action: "word_settings", enabled: false}, false);
                } else if (phase === 113) {
                    const restored = freshView.item;
                    if (restored.definitionsEnabled) throw Error("Dictionary disable did not persist");
                    const field = find(restored, "typing-input");
                    const before = field.text;
                    field.forceActiveFocus();
                    const currentWord = restored.currentWordItem();
                    keyDriver.keyClick(Qt.Key_Space, Qt.ControlModifier, 0);
                    keyDriver.wait(30);
                    const panel = restored.wordTools;
                    if (!panel.opened || restored.selectedTerm.toLowerCase() !== currentWord.modelData.text.trim().toLowerCase() || field.text !== before)
                        throw Error("Ctrl+Space did not inspect the current word without editing input: " + JSON.stringify({opened:panel.opened, term:restored.selectedTerm, expected:currentWord.modelData.text, before:before, after:field.text}));
                    if (panel.anchor.item !== restored.menuAnchorItem || panel.anchor.rect.x !== 0 || Math.abs(panel.anchor.rect.y - restored.menuAnchorItem.height - 6) > 1 || Math.abs(panel.width - restored.menuAnchorItem.width) > 1 || Math.abs(panel.height - restored.menuAnchorItem.height) > 1) throw Error("Word menu does not match the typing panel or sit below it");
                    if (panel.surface.variant !== "bg") throw Error("Word panel does not share the typing surface theme");
                    keyDriver.keyClick(Qt.Key_Space, Qt.ControlModifier, 0);
                    keyDriver.wait(30);
                    if (panel.opened || !field.activeFocus) throw Error("Ctrl+Space did not close word panel and restore typing focus");
                    restored.openWord("“Macy,”");
                } else if (phase === 114) {
                    const restored = freshView.item;
                    if (!restored.noteLoaded) return;
                    if (restored.selectedTerm !== "macy" || restored.definitionRequest !== null) throw Error("Word selection or disabled dictionary failed");
                    if (find(restored, "typing-word-search").visible || find(restored, "typing-word-note").visible || find(restored, "typing-definitions-toggle").visible) throw Error("Word panel did not hide secondary controls");
                    find(restored, "typing-edit-word-note").clicked();
                    if (!find(restored, "typing-word-note").visible) throw Error("Add note did not open the editor");
                    find(restored, "typing-word-note").text = "Character reminder";
                    find(restored, "typing-save-word-note").clicked();
                } else if (phase === 115) {
                    const restored = freshView.item;
                    if (restored.noteSaving) return;
                    if (restored.noteDirty || restored.savedWordNote !== "Character reminder") throw Error("Word note did not save");
                    find(restored, "typing-word-panel").close();
                    restored.openWord("MACY");
                } else if (phase === 116) {
                    const restored = freshView.item;
                    if (!restored.noteLoaded) return;
                    if (find(restored, "typing-word-note").text !== "Character reminder" || restored.notedTerms[0] !== "macy" || find(restored, "typing-saved-words").textAt(0) !== "macy") throw Error("Word note did not reopen");
                    if (!find(restored, "typing-word-note-preview").visible || find(restored, "typing-word-note-preview").text !== "Character reminder") throw Error("Saved note is missing from compact view");
                    find(restored, "typing-word-options").clicked();
                    if (!find(restored, "typing-word-search").visible || !find(restored, "typing-definitions-toggle").visible) throw Error("More did not reveal word options");
                    find(restored, "typing-word-panel").close();
                    const field = find(restored, "typing-input");
                    const glyph = find(restored, "typing-character-0");
                    const point = glyph.mapToItem(field, glyph.width / 2, glyph.height / 2);
                    keyDriver.mouseClick(field, point.x, point.y, Qt.RightButton);
                } else if (phase === 117) {
                    const restored = freshView.item;
                    if (!find(restored, "typing-word-panel").opened || !restored.selectedTerm) throw Error("Right click did not open word tools");
                    if (restored.definitionRequest !== null) throw Error("Disabled dictionary made a request");
                    restored.createDictionaryRequest = function() {
                        return {
                            readyState: 0, status: 200,
                            responseText: JSON.stringify([{meanings: [{partOfSpeech: "noun", definitions: [{definition: "A test definition."}]}]}]),
                            open: function(method, url) { if (method !== "GET" || !url.endsWith(encodeURIComponent(restored.selectedTerm))) throw Error("Wrong dictionary URL"); },
                            abort: function() {},
                            send: function() { const request = this; Qt.callLater(() => { request.readyState = XMLHttpRequest.DONE; request.onreadystatechange(); }); }
                        };
                    };
                    restored.definitionsEnabled = true;
                    restored.lookupDefinition();
                } else if (phase === 118) {
                    const restored = freshView.item;
                    if (!restored.definitionText.includes("A test definition.") || restored.definitionRequest !== null) throw Error("Definition response did not render");
                    restored.definitionsEnabled = false;
                    restored.lookupDefinition();
                    if (restored.definitionText !== "" || restored.definitionRequest !== null) throw Error("Dictionary off did not clear lookup");
                    let aborted = false;
                    restored.definitionRequest = {abort: function() { aborted = true; }};
                    restored.openWord("");
                    if (!aborted || restored.definitionRequest !== null) throw Error("Changing terms did not cancel old definition");
                    restored.openNotebook();
                } else if (phase === 119) {
                    const restored = freshView.item;
                    if (Math.abs(restored.wordTools.width - restored.menuAnchorItem.width) > 1 || Math.abs(restored.wordTools.height - restored.menuAnchorItem.height) > 1) throw Error("Notebook size does not match the typing panel");
                    if (!restored.notebookBrowsing || restored.noteEntries.length !== 1 || restored.noteEntries[0].category !== "General") throw Error("Book notebook did not load existing notes");
                    restored.notebookFilter = "People";
                    if (restored.visibleNoteEntries.length !== 0) throw Error("Notebook sections do not filter entries");
                    const search = find(restored, "typing-word-term");
                    search.text = "No matching name";
                    search.accepted();
                    if (!restored.notebookBrowsing || restored.selectedTerm) throw Error("Searching unexpectedly created a note");
                    find(restored, "typing-new-notebook-note").clicked();
                    if (!restored.notebookCreating || search.text) throw Error("New note did not open a separate blank title form");
                    search.text = "Elliot";
                    find(restored, "typing-new-notebook-note").clicked();
                } else if (phase === 120) {
                    const restored = freshView.item;
                    if (!restored.noteLoaded) return;
                    if (!restored.notebookMode || restored.notebookBrowsing || restored.noteCategory !== "People" || restored.definitionRequest !== null) throw Error("New categorized notebook entry failed");
                    if (!restored.editingWordNote) throw Error("New notebook entry did not open its editor");
                    const actions = find(restored, "typing-note-actions");
                    const scroll = find(restored, "typing-word-scroll");
                    if (!actions.visible || actions.y < scroll.y + scroll.height - 1) throw Error("Save controls are not pinned below the scroll region");
                    if (!find(restored, "typing-note-category").visible || !find(restored, "typing-note-template").visible) throw Error("Section selector or prompts missing");
                    find(restored, "typing-note-template").clicked();
                    if (!find(restored, "typing-word-note").text.includes("Relationships:")) throw Error("People prompts did not populate note");
                    find(restored, "typing-word-note").text += "A childhood friend.";
                    restored.saveWordNote();
                } else if (phase === 121) {
                    const restored = freshView.item;
                    if (restored.noteSaving) return;
                    if (restored.savedNoteCategory !== "People" || !restored.savedWordNote.includes("childhood friend")) throw Error("Categorized note did not save");
                    find(restored, "typing-notebook-back").clicked();
                } else if (phase === 122) {
                    const restored = freshView.item;
                    if (restored.visibleNoteEntries.length !== 1 || restored.visibleNoteEntries[0].term !== "elliot") throw Error("Saved note did not appear in People section");
                    restored.notebookFilter = "Mysteries";
                    if (restored.visibleNoteEntries.length !== 0) throw Error("People note leaked into Mysteries section");
                    restored.notebookFilter = "People";
                    keyDriver.wait(40);
                    const card = find(restored, "typing-notebook-entry-elliot");
                    if (!card) throw Error("Notebook entry card is missing");
                    keyDriver.mouseClick(card, card.width / 2, card.height / 2, Qt.LeftButton);
                    keyDriver.wait(40);
                    if (restored.notebookBrowsing) throw Error("Notebook card click did not open entry: " + JSON.stringify({width:card.width,height:card.height,visible:card.visible}));
                } else if (phase === 123) {
                    const restored = freshView.item;
                    if (!restored.noteLoaded) return;
                    if (restored.notebookBrowsing || restored.selectedTerm !== "elliot" || restored.savedNoteCategory !== "People") throw Error("Clicking a notebook entry did not reopen its note");
                    const originalNote = restored.savedWordNote;
                    find(restored, "typing-edit-word-note").clicked();
                    find(restored, "typing-word-note").text = "Unsaved replacement";
                    find(restored, "typing-cancel-note-edit").clicked();
                    if (restored.noteDirty || restored.editingWordNote || find(restored, "typing-word-note").text !== originalNote) throw Error("Cancel did not restore the saved note");
                    restored.wordTools.close();
                    expectedPosition = restored.position;
                    restored.toggleFullscreen();
                } else if (phase === 124) {
                    const restored = freshView.item;
                    const reader = find(restored, "reader-page-text");
                    if (!reader.visible || !reader.readOnly || find(restored, "typing-input").visible || find(restored, "typing-live-wpm").visible) throw Error("Reading mode still exposes typing controls");
                    if (reader.font.family !== "Noto Serif" || reader.width > 720 || reader.getText(0, reader.length).trim() !== restored.passage.trim()) throw Error("Reader typography, measure, or displayed text is incorrect");
                    const escaped = restored.readerHtml('<img src="missing"> & book');
                    if (escaped.includes('<img') || !escaped.includes('&lt;img') || !escaped.includes('&amp;')) throw Error("Book markup was not escaped for reader formatting");
                    restored.grabToImage(result => result.saveToFile("/tmp/enclosure-reader-preview.png"));
                    reader.forceActiveFocus();
                    const original = reader.text;
                    keyDriver.keyClick(Qt.Key_A, Qt.NoModifier, 0);
                    if (reader.text !== original) throw Error("Reader allowed text editing");
                    find(restored, "reader-next-page").clicked();
                } else if (phase === 125) {
                    const restored = freshView.item;
                    if (restored.busy) return;
                    if (restored.position <= expectedPosition || find(restored, "typing-input").text.length) throw Error("Reading next page did not navigate without typing");
                    find(restored, "reader-previous-page").clicked();
                } else if (phase === 126) {
                    const restored = freshView.item;
                    if (restored.busy) return;
                    if (restored.position !== expectedPosition) throw Error("Reader previous page lost its exact position");
                    restored.handleEscape();
                    if (restored.fullscreen || !find(restored, "typing-input").visible) throw Error("Escape did not restore typing mode");
                    console.log("PASS: categorized book notebook, templates, word selection, saved notes, dictionary toggle, available-height passage fitting, lossless paging, Backspace navigation, queued input, legacy bookmark carryover, no-fail advance, resume, WPM and EPUB import");
                    Qt.quit();
                }

                phase++;
            } catch (error) { console.error("Phase " + phase + ": " + error + "\n" + error.stack); Qt.quit(); }
            finally { stepping = false; }
        }
    }
}
