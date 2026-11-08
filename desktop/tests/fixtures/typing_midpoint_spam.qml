import QtQuick
import QtQuick.Window
import Quickshell
ShellRoot {
    Window {
        visible: true
        width: 800; height: 640
        TypingMenu { id: practice; anchors.fill: parent }
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
                    const later = practice.pageLayout.words.find(word => word.line * practice.passageLineHeight > middle + practice.passageLineHeight);
                    input.text = practice.passage.slice(0, later.start); input.cursorPosition = input.length;
                    practice.syncCaret();
                    const screenY = later.line * practice.passageLineHeight + scroll.centerPadding - scroll.contentY;
                    if (scroll.contentY <= 0 || Math.abs(screenY - middle) > 1) throw Error("Active row was not kept at midpoint");
                    practice.fullscreen = false; practice.fitPage(); phase++; return;
                }
                if (phase === 2) {
                    const later = practice.pageLayout.words.find(word => word.line === 5);
                    input.text = practice.passage.slice(0, later.start); input.cursorPosition = input.length;
                    practice.syncCaret();
                    if (scroll.contentY <= 0 || Math.abs(5 * practice.passageLineHeight + scroll.centerPadding - scroll.contentY - middle) > 1)
                        throw Error("Small menu did not scroll at midpoint");
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
                    console.log("PASS: midpoint scrolling in both sizes, rapid keys retained, transition buffering and Unicode backspace");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
