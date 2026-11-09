import QtQuick
import QtTest
import Quickshell
ShellRoot {
    PanelWindow {
        implicitWidth: 640; implicitHeight: 480
        TypingMenu { id: menu; anchors.fill: parent }
    }
    TestCase { id: input; when: false }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const found = find(child, name); if (found) return found; }
        return null;
    }
    function press(key) {
        const reader = find(menu, "reader-page-text");
        input.parent = reader; reader.forceActiveFocus();
        input.keyClick(key, Qt.ControlModifier);
    }
    Timer {
        interval: 100; repeat: true; running: true
        property int phase: 0
        property int ticks: 0
        property int hold: 0
        property int originalWord: 0
        property real originalRow: 0
        property real lowerRow: 0
        onTriggered: {
            try {
                if (++ticks > 200) throw Error("Reader word test timed out at phase " + phase);
                if (phase === 0) {
                    menu.wordTools.grabFocus = false; // Synthetic events have no Wayland grab serial.
                    menu.readingMode = true;
                    menu.send({action: "add", title: "Reader words", text: "Alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu. ".repeat(20)});
                    phase++; return;
                }
                const reader = find(menu, "reader-page-text");
                if (phase === 1) {
                    if (menu.busy || !menu.passage.length || ++hold < 5) return;
                    reader.cursorPosition = 0;
                    menu.speechActive = true; menu.speechSourceOffset = 0; menu.speechText = menu.passage;
                    originalWord = menu.passage.indexOf("charlie");
                    menu.updateSpeechHighlight({start: originalWord, end: originalWord + 7});
                    press(Qt.Key_Space);
                    if (!menu.wordTools.opened || menu.selectedTerm !== "charlie") throw Error("Lookup ignored the spoken word at a different cursor position");
                    phase++; return;
                }
                if (phase === 2) {
                    if (!menu.noteLoaded) return;
                    menu.wordTools.close(); menu.speechPaused = true;
                    press(Qt.Key_L);
                    if (menu.passage.slice(menu.speechHighlightStart, menu.speechHighlightEnd) !== "delta") throw Error("Ctrl+L did not move right by word");
                    press(Qt.Key_H);
                    if (menu.speechHighlightStart !== originalWord) throw Error("Ctrl+H did not move left by word");
                    originalRow = reader.positionToRectangle(menu.speechHighlightStart).y;
                    press(Qt.Key_J);
                    lowerRow = reader.positionToRectangle(menu.speechHighlightStart).y;
                    if (lowerRow <= originalRow) throw Error("Ctrl+J did not move to the line below");
                    press(Qt.Key_J);
                    if (reader.positionToRectangle(menu.speechHighlightStart).y <= lowerRow) throw Error("Repeated Ctrl+J did not move another line");
                    press(Qt.Key_K);
                    if (reader.positionToRectangle(menu.speechHighlightStart).y !== lowerRow) throw Error("Ctrl+K skipped a displayed line");
                    press(Qt.Key_K);
                    if (menu.speechHighlightStart !== originalWord) throw Error("Vertical navigation lost its original column");
                    const highlight = find(reader, "reader-spoken-highlight-0");
                    if (!highlight || highlight.width <= 0 || reader.selectedText.length) throw Error("Word navigation did not use the visible active highlight");
                    press(Qt.Key_Space);
                    if (menu.selectedTerm !== "charlie") throw Error("Lookup ignored keyboard word navigation");
                    phase++; return;
                }
                if (phase === 3) {
                    if (!menu.noteLoaded) return;
                    menu.wordTools.close(); menu.stopSpeech();
                    reader.cursorPosition = 0;
                    press(Qt.Key_H);
                    if (menu.speechHighlightStart !== 0) throw Error("Left navigation escaped the page");
                    press(Qt.Key_K);
                    if (menu.speechHighlightStart !== 0) throw Error("Up navigation escaped the page");
                    reader.select(6, 11);
                    if (menu.speechHighlightStart !== -1) throw Error("Explicit selection retained a stale word highlight");
                    menu.openCurrentWord();
                    if (menu.selectedTerm !== "bravo") throw Error("Explicit selection lookup no longer works");
                    phase++; return;
                }
                if (phase === 4) {
                    if (!menu.noteLoaded) return;
                    menu.wordTools.close(); menu.readingMode = false;
                    if (menu.readerKey({key: Qt.Key_J, modifiers: Qt.ControlModifier})) throw Error("Reader word navigation intercepted typing mode");
                    console.log("PASS: spoken-word lookup, Ctrl+H/J/K/L keys, displayed rows and column, page boundaries, explicit selection and typing isolation");
                    Qt.quit();
                }
            } catch (error) { console.error("FAIL:", error); Qt.exit(1); }
        }
    }
}
