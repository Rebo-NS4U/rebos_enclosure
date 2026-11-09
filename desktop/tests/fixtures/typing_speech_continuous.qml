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
        interval: 100; running: true; repeat: true
        property int phase: 0
        property int ticks: 0
        property int lastPosition: -1
        property int expectedPosition: 0
        property int spokenPages: 0
        property int hold: 0
        property int stoppedPosition: 0
        onTriggered: {
            try {
                if (++ticks > 500) throw Error("Continuous speech timed out in phase " + phase);
                if (phase === 0) {
                    menu.readingMode = true;
                    menu.send({action: "add", title: "Continuous speech", text: "Chapter 1\n\n" + "A measured voice carries the story forward. ".repeat(75) + "\n\nChapter 2\n\n" + "The second chapter brings the story to its ending. ".repeat(45)});
                    phase++; return;
                }
                if (phase === 1) {
                    if (menu.busy || !menu.bookId || !menu.passage.length || ++hold < 5) return;
                    if (menu.speechProfile !== "kokoro-nicole") throw Error("Kokoro Nicole preset is not default");
                    menu.toggleSpeech(); phase++; return;
                }
                if (phase === 2) {
                    if (menu.speaking && !menu.speechAdvancing && !menu.busy && menu.position !== lastPosition) {
                        if (menu.position !== expectedPosition) throw Error("Continuous speech skipped or repeated text: position=" + menu.position + " expected=" + expectedPosition + " pageEnd=" + menu.speechPageEnd);
                        lastPosition = menu.position;
                        expectedPosition += menu.characters(menu.passage).length;
                        spokenPages++;
                    }
                    if (menu.speaking) return;
                    if (spokenPages < 3 || expectedPosition !== menu.bookLength || menu.currentChapterIndex < 1) throw Error("Did not read every page through the last chapter: pages=" + spokenPages + " spoken=" + expectedPosition + " length=" + menu.bookLength + " position=" + menu.position + " chapter=" + menu.currentChapterIndex + " error=" + menu.errorMessage);
                    menu.seek(0); hold = 0; phase++; return;
                }
                if (phase === 3) {
                    if (menu.busy || ++hold < 5) return;
                    menu.toggleSpeech(); phase++; return;
                }
                if (phase === 4) {
                    if (!menu.speechAdvancing) return;
                    const stop = find(menu, "reader-speech-stop");
                    if (stop.text !== "Stop" || !stop.enabled) throw Error("Stop unavailable between pages");
                    stop.clicked(); hold = 0; phase++; return;
                }
                if (phase === 5) {
                    if (menu.busy || ++hold < 8) return;
                    if (menu.speaking || menu.speechActive) throw Error("Stopped read-aloud resumed after a page loaded");
                    menu.seek(0); hold = 0; phase++; return;
                }
                if (phase === 6) {
                    if (menu.busy || ++hold < 5) return;
                    menu.toggleSpeech(); menu.readNextPage(); hold = 0; phase++; return;
                }
                if (phase === 7) {
                    if (menu.busy || ++hold < 6) return;
                    if (menu.speaking) throw Error("Manual page turn did not cancel narration");
                    const reader = find(menu, "reader-page-text");
                    reader.select(0, 12);
                    stoppedPosition = menu.position;
                    menu.toggleSpeech(); hold = 0; phase++; return;
                }
                if (phase === 8) {
                    if (++hold < 8) return;
                    if (menu.speaking || menu.position !== stoppedPosition) throw Error("Selected text advanced to another page");
                    menu.speechActive = true; menu.speechContinuous = true;
                    menu.speakPage("FAIL_PLAYBACK"); hold = 0; phase++; return;
                }
                if (phase === 9) {
                    if (++hold < 8) return;
                    if (menu.speaking || !menu.errorMessage.length) throw Error("Playback failure did not stop narration");
                    menu.errorMessage = "";
                    find(menu, "reader-page-text").deselect();
                    menu.toggleSpeech(); phase++; return;
                }
                if (phase === 10) {
                    if (!menu.speechAdvancing) return;
                    menu.receive(JSON.stringify({action: "seek", id: menu.bookId, request: menu.pageRequest, error: "Test page-load failure"}));
                    hold = 0; phase++; return;
                }
                if (phase === 11) {
                    if (++hold < 8) return;
                    if (menu.speaking) throw Error("Page-load failure did not cancel continuous narration");
                    console.log("PASS: Kokoro Nicole default; continuous pages and chapters without skips, end-of-book stop, gap stop, manual navigation, selection-only playback, playback/load error cancellation");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
