import QtQuick
import Quickshell
ShellRoot {
    PanelWindow {
        implicitWidth: 640; implicitHeight: 480
        TypingMenu { id: menu; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        interval: 80; running: true; repeat: true
        property int phase: 0
        property int ticks: 0
        property int hold: 0
        property int lastWord: -1
        property bool moved: false
        property bool captured: false
        onTriggered: {
            try {
                if (++ticks > 400) throw Error("Highlight test timed out in phase " + phase);
                if (phase === 0) {
                    menu.readingMode = true;
                    menu.send({action: "add", title: "Highlight test", text: "A voice follows each word across the page. ".repeat(45)});
                    phase++; return;
                }
                const reader = find(menu, "reader-page-text");
                if (phase === 1) {
                    if (menu.busy || !menu.bookId || ++hold < 6) return;
                    menu.toggleSpeech(); phase++; return;
                }
                if (phase === 2) {
                    if (menu.speechAdvancing && menu.speechHighlightStart >= 0) throw Error("Highlight leaked between pages");
                    if (menu.speechHighlightStart < 0) return;
                    if (reader.selectedText) throw Error("Narration changed user selection");
                    if (menu.speechHighlightEnd > menu.passage.length) throw Error("Highlight escaped page bounds");
                    const rect = find(reader, "reader-spoken-highlight-0");
                    if (!rect || rect.width <= 0 || rect.height <= 0) return;
                    if (lastWord >= 0 && menu.speechHighlightStart !== lastWord) moved = true;
                    lastWord = menu.speechHighlightStart;
                    if (!captured) {
                        captured = true;
                        reader.grabToImage(result => result.saveToFile("/tmp/enclosure-spoken-word.png"));
                    }
                    if (menu.position <= 0 || !moved) return;
                    menu.stopSpeech(); hold = 0; phase++; return;
                }
                if (phase === 3) {
                    if (++hold < 4) return;
                    menu.updateSpeechHighlight({start: 0, end: 4});
                    if (menu.speechHighlightStart !== -1) throw Error("Stop retained or accepted a stale cue");
                    reader.select(3, 18);
                    menu.toggleSpeech(); phase++; return;
                }
                if (phase === 4) {
                    if (menu.speechHighlightStart < 0) return;
                    if (menu.speechHighlightStart < 3 || menu.speechHighlightEnd > 18 || !reader.selectedText) throw Error("Selected-text highlighting lost its source range");
                    menu.speechProfile = "kokoro-bella";
                    if (menu.speechHighlightStart !== -1) throw Error("Voice change retained highlight");
                    hold = 0; phase++; return;
                }
                if (phase === 5) {
                    if (++hold < 4) return;
                    menu.previewSpeech(); phase++; return;
                }
                if (phase === 6) {
                    if (menu.speechHighlightStart !== -1) throw Error("Voice preview highlighted the book");
                    menu.stopSpeech();
                    console.log("PASS: moving word highlight, geometry, page continuation/reset, selection offsets, stale cue cancellation, voice change and preview isolation");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
