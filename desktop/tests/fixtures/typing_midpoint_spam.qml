import QtQuick
import QtQuick.Window
import Quickshell
ShellRoot {
    Window {
        visible: true
        width: 800; height: 640
        TypingMenu { id: practice; anchors.fill: parent; viewportHeight: 720 }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        interval: 300; running: true; repeat: true
        property int phase: 0
        onTriggered: {
            try {
                const input = find(practice, "typing-input");
                const scroll = find(practice, "typing-page-visuals");
                if (phase === 0) {
                    practice.practicing = true; practice.fullscreen = true;
                    practice.pageSource = "A sequence of words for rapid typing. ".repeat(200);
                    practice.fitPage(); phase++; return;
                }
                const middle = (scroll.height - practice.passageLineHeight) / 2;
                if (phase === 1) {
                    const early = practice.pageLayout.words.find(word => word.line === 1);
                    input.text = practice.passage.slice(0, early.start); input.cursorPosition = input.length;
                    practice.syncCaret();
                    if (scroll.contentY !== 0) throw Error("Scrolled before the middle");
                    const later = practice.pageLayout.words.find(word => word.line * practice.passageLineHeight + scroll.centerPadding > middle);
                    input.text = practice.passage.slice(0, later.start); input.cursorPosition = input.length;
                    practice.syncCaret();
                    const screenY = later.line * practice.passageLineHeight + scroll.centerPadding - scroll.contentY;
                    if (scroll.contentY <= 0 || Math.abs(screenY - middle) > 1) throw Error("Fullscreen row did not center at the midpoint");
                    practice.fullscreen = false; practice.fitPage(); phase++; return;
                }
                if (phase === 2) {
                    practice.pageSource = ("A sequence of words for rapid typing.\n").repeat(30);
                    practice.fitPage();
                    const newline = practice.pageLayout.words.find(word => word.line === 4 && word.text === "\n");
                    input.text = practice.passage.slice(0, newline.start); input.cursorPosition = input.length;
                    practice.focusPassage(); phase++; return;
                }
                if (phase === 3) {
                    const newline = practice.pageLayout.words.find(word => word.line === 4 && word.text === "\n");
                    const nextGlyph = practice.glyphItems[newline.start + 2];
                    if (!nextGlyph) throw Error("Next row was not rendered");
                    if (!practice.handleWhitespaceKey({key: Qt.Key_Return, modifiers: 0})
                            || input.text !== practice.passage.slice(0, newline.start + 1))
                        throw Error("Return did not insert the required newline");
                    if (practice.scrollLine !== 5 || Math.abs(nextGlyph.opacity - 0.85) > 0.001)
                        throw Error("Return did not highlight the next row immediately");
                    if (Math.abs(5 * practice.passageLineHeight + scroll.centerPadding - scroll.contentY - middle) > 1)
                        throw Error("Return did not center the active row");
                    const nextReturn = practice.pageLayout.words.find(word => word.line === 5 && word.text === "\n");
                    input.text = practice.passage.slice(0, nextReturn.start); input.cursorPosition = input.length;
                    const beforeNextReturn = scroll.contentY;
                    practice.handleWhitespaceKey({key: Qt.Key_Return, modifiers: 0});
                    if (Math.abs(scroll.contentY - beforeNextReturn - practice.passageLineHeight) > 1
                            || Math.abs(6 * practice.passageLineHeight + scroll.centerPadding - scroll.contentY - middle) > 1)
                        throw Error("Return did not keep the next row centered");
                    input.text = ""; input.cursorPosition = 0;
                    practice.focusPassage();
                    const started = Date.now();
                    for (let index = 0; index < 200; index++)
                        practice.handleTypingEditKey({key: Qt.Key_X, text: "x", modifiers: 0});
                    if (input.text !== "x".repeat(200)) throw Error("Rapid keys lost or reordered");
                    const elapsed = Date.now() - started;
                    console.log("SPAM 200 keys ms", elapsed);
                    if (elapsed / 200 > 30) throw Error("Rapid input exceeded per-key latency budget");
                    practice.turningPage = true; practice.busy = true;
                    for (let index = 0; index < 200; index++)
                        practice.handleTypingEditKey({key: Qt.Key_A, text: "a", modifiers: 0});
                    practice.handleTypingEditKey({key: Qt.Key_Backspace, text: "", modifiers: 0});
                    practice.handleWhitespaceKey({key: Qt.Key_Tab, text: "", modifiers: 0});
                    practice.handleWhitespaceKey({key: Qt.Key_Return, text: "", modifiers: 0});
                    if (input.text !== "x".repeat(200) || practice.pendingKeys !== "a".repeat(199) + "\t\n") throw Error("Transition buffer lost input");
                    practice.queueTyping("😀"); practice.undoQueuedKey();
                    if (!practice.pendingKeys.endsWith("\t\n")) throw Error("Queued Unicode backspace split a character");
                    console.log("PASS: centered compact and fullscreen rows, immediate Return highlighting, rapid keys retained, transition buffering and Unicode backspace");
                    running = false;
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
