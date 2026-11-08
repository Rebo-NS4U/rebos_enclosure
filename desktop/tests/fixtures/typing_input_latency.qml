import QtQuick
import QtQuick.Window
import Quickshell
import "TypingPaging.js" as Pages
ShellRoot {
    Window {
        visible: true
        width: 640; height: 600
        TypingMenu { id: practice; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        interval: 16; running: true; repeat: true
        property int tick: 0
        property int keys: 0
        property int phase: 0
        property real cost: 0
        property real maximum: 0
        property real shortAverage: 0
        onTriggered: {
            try {
                if (tick++ === 0) {
                    practice.practicing = true; practice.bookId = "latency-fixture"; practice.bookLength = 1000000;
                    practice.pageSource = "Some words to type with punctuation and spaces. ".repeat(120);
                    practice.fitPage(); return;
                }
                if (tick < 25) return;
                const input = find(practice, "typing-input");
                if (keys === 0) {
                    practice.restoring = true;
                    input.text = phase === 0 ? "" : practice.passage.slice(0, 1000);
                    input.cursorPosition = input.length;
                    practice.restoring = false; practice.refreshPageCaret(); practice.focusPassage();
                }
                const started = Date.now();
                input.insert(input.length, practice.passage.charAt(input.length));
                const elapsed = Date.now() - started;
                cost += elapsed; maximum = Math.max(maximum, elapsed);
                if (++keys === 100) {
                    console.log("LATENCY", phase === 0 ? "short" : "1000-character prefix", "averageMs", cost / keys, "maxMs", maximum);
                    if (phase === 0) shortAverage = cost / keys;
                    else if (cost / keys > Math.max(30, shortAverage * 3))
                        throw Error("Long-input latency grew beyond budget");
                    keys = 0; cost = 0; maximum = 0;
                    if (++phase === 2) {
                        if (Pages.prepareInput("Wait...", "Wait…").text !== "Wait…"
                                || !Pages.prepareInput("Wait..", "Wait…").pending
                                || Pages.prepareInput("...", "...").text !== "...")
                            throw Error("Ellipsis composition changed");
                        practice.restoring = true;
                        practice.pageSource = "“😀…"; practice.fitPage();
                        input.text = '"😀…'; input.cursorPosition = input.length;
                        if (practice.correctCount() !== 3) throw Error("Cached Unicode/quote accuracy wrong");
                        input.text = "x";
                        if (practice.correctCount() !== 0) throw Error("Accuracy did not invalidate on correction");
                        console.log("PASS: bounded long-input latency, ellipsis composition, and cached accuracy"); Qt.quit();
                    }
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
