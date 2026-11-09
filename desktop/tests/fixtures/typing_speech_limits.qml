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
    Timer {
        interval: 100; running: true; repeat: true
        property int phase: 0
        property int ticks: 0
        property int hold: 0
        onTriggered: {
            try {
                if (++ticks > 500) throw Error("Reading limits timed out at phase " + phase);
                if (phase === 0) {
                    menu.readingMode = true;
                    menu.send({action: "add", title: "Reading limits", text: "Chapter 1\n\n" + "Alpha words fill the first chapter. ".repeat(12) + "\n\nChapter 2\n\n" + "Beta words fill the second chapter. ".repeat(12) + "\n\nChapter 3\n\n" + "Gamma words complete the final chapter. ".repeat(12)});
                    phase++; return;
                }
                if (phase === 1) {
                    if (menu.busy || !menu.bookId || ++hold < 5) return;
                    if (menu.chapters.length !== 3) throw Error("Missing test chapters");
                    menu.speechLimitMode = "chapter";
                    menu.toggleSpeech(); phase++; return;
                }
                if (phase === 2) {
                    if (menu.speechText.includes("Beta")) throw Error("Spoke beyond next-chapter limit");
                    if (menu.speaking || menu.busy) return;
                    if (menu.position !== menu.chapters[1].position) throw Error("Next chapter not ready after stopping");
                    menu.seek(0); menu.speechLimitMode = "chapters"; hold = 0;
                    menu.readerMenu.open(); phase++; return;
                }
                if (phase === 3) {
                    if (menu.busy || ++hold < 5) return;
                    const number = find(menu.readerMenu.contentItem, "reader-limit-count");
                    if (!number.visible || number.value !== 2) throw Error("Chapter count field missing");
                    input.mouseClick(number.up.indicator, 16, 18);
                    if (menu.speechChapterCount !== 3) throw Error("Chapter counter increment failed");
                    input.mouseClick(number.down.indicator, 16, 18);
                    if (menu.speechChapterCount !== 2) throw Error("Chapter counter decrement failed");
                    menu.readerMenu.close(); menu.toggleSpeech(); phase++; return;
                }
                if (phase === 4) {
                    if (menu.speechText.includes("Gamma")) throw Error("Spoke beyond two-chapter limit");
                    if (menu.speaking || menu.busy) return;
                    if (menu.position !== menu.chapters[2].position) throw Error("Chapter count stopped at wrong boundary");
                    menu.speechLimitMode = "time"; menu.readerMenu.open();
                    menu.seek(0); hold = 0; phase++; return;
                }
                if (phase === 5) {
                    if (menu.busy || ++hold < 5) return;
                    const minutes = find(menu.readerMenu.contentItem, "reader-limit-count");
                    input.parent = minutes.contentItem;
                    minutes.contentItem.forceActiveFocus();
                    input.keyClick(Qt.Key_A, Qt.ControlModifier);
                    input.keyClick(Qt.Key_1);
                    input.keyClick(Qt.Key_Return);
                    if (menu.speechMinutes !== 1) throw Error("Typed minute value did not commit");
                    menu.readerMenu.close();
                    menu.toggleSpeech();
                    if (menu.speechDeadline - Date.now() < 59000) throw Error("Minute limit was not converted correctly");
                    // Accelerate this session's deadline, exercising the real timer.
                    menu.speechDeadline = Date.now() + 450;
                    hold = 0; phase++; return;
                }
                if (phase === 6) {
                    if (++hold < 12) return;
                    if (menu.speaking || menu.speechDeadline !== 0 || menu.speechHighlightStart !== -1) throw Error("Timer did not stop session and clear state");
                    menu.speechLimitMode = "page"; menu.seek(0); hold = 0; phase++; return;
                }
                if (phase === 7) {
                    if (menu.busy || ++hold < 5) return;
                    menu.toggleSpeech(); phase++; return;
                }
                if (phase === 8) {
                    if (menu.speaking) return;
                    if (menu.position !== 0) throw Error("Current-page limit advanced the book");
                    menu.speechLimitMode = "time";
                    menu.previewSpeech();
                    if (menu.speechDeadline !== 0) throw Error("Preview started a reading timer");
                    menu.stopSpeech();
                    menu.speechLimitMode = "none"; hold = 0; phase++; return;
                }
                if (phase === 9) {
                    if (++hold < 5) return;
                    menu.toggleSpeech();
                    if (menu.speechDeadline !== 0 || menu.speechStopPosition !== menu.bookLength) throw Error("Unlimited mode retained old limits");
                    menu.speechLimitMode = "chapter";
                    if (menu.speechActive) throw Error("Changing limits retained the active session");
                    hold = 0; phase++; return;
                }
                if (phase === 10) {
                    if (++hold < 4) return;
                    if (menu.speaking) throw Error("Changing limits did not stop current session");
                    console.log("PASS: next chapter, multiple chapters, count controls, minute conversion and timer expiry, page-only, preview isolation, unlimited reset and limit-change cancellation");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
