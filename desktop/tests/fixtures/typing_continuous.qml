import QtQuick
import Quickshell
ShellRoot {
    PanelWindow {
        implicitWidth: 640
        implicitHeight: 600
        TypingMenu { id: practice; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const found = find(child, name); if (found) return found; }
        return null;
    }
    Timer {
        interval: 500; running: true; repeat: true
        property int phase: 0
        property int polls: 0
        property int expectedPosition: 0
        property string expectedInput: ""
        property string expectedPassage: ""
        onTriggered: {
            try {
                if (++polls > 50) throw Error("Continuous typing timed out");
                if (phase === 0) {
                    practice.send({action: "add", title: "Bounded continuous test",
                        text: "Chapter One\n\n" + "Some words with emoji 😀 to type continuously. ".repeat(1000)
                            + "\n\nChapter Two\n\nThe end."});
                    phase++; return;
                }
                if (practice.busy) return;
                const input = find(practice, "typing-input");
                if (phase === 1) {
                    if (!practice.bookId) return;
                    if (practice.pageSource.length > 8192 || practice.pageLayout.lines > 36)
                        throw Error("Loading or layout is unbounded");
                    const words = practice.pageLayout.words;
                    const cursor = words.find(word => word.line >= practice.pageLayout.lines - 7).start;
                    const start = words.find(word => word.line >= practice.pageLayout.lines - 14).start;
                    expectedPosition = practice.characters(practice.passage.slice(0, start)).length;
                    expectedInput = practice.passage.slice(start, cursor);
                    expectedPassage = practice.passage.slice(start);
                    practice.restoring = true;
                    input.text = practice.passage.slice(0, cursor);
                    input.cursorPosition = input.length;
                    practice.restoring = false;
                    practice.advance(); phase++; return;
                }
                if (phase === 2) {
                    if (practice.position !== expectedPosition || input.text !== expectedInput)
                        throw Error("Overlapping window lost position or input");
                    if (!practice.passage.startsWith(expectedPassage)) throw Error("Visible context changed");
                    if (practice.pageTransitions !== 0) throw Error("Page reset inside chapter");
                    if (practice.chapterProgress <= practice.progress) throw Error("Chapter progress is not independent");
                    if (practice.pageSource.length > 8192 || practice.pageLayout.lines > 36)
                        throw Error("Rolling window grew unbounded");
                    practice.fullscreen = true;
                    phase++; return;
                }
                if (phase === 3) {
                    if (practice.position !== expectedPosition || input.text !== expectedInput)
                        throw Error("Fullscreen font reflow lost saved progress");
                    practice.saveProgress();
                    console.log("PASS: bounded continuous windows preserve context, input, chapter progress, page transitions and fullscreen font reflow");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
