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
    function space(repeat) { menu.readerKey({key: Qt.Key_Space, modifiers: Qt.NoModifier, isAutoRepeat: !!repeat}); }
    Timer {
        interval: 100; repeat: true; running: true
        property int phase: 0
        property int ticks: 0
        property int hold: 0
        property double originalDeadline: 0
        property int originalPosition: 0
        onTriggered: {
            try {
                if (++ticks > 250) throw Error("Pause test timed out at phase " + phase);
                if (phase === 0) {
                    menu.readingMode = true;
                    menu.send({action: "add", title: "Space playback", text: "Words remain on the page while reading is paused. ".repeat(100)});
                    phase++; return;
                }
                if (phase === 1) {
                    if (menu.busy || !menu.bookId || ++hold < 5) return;
                    menu.speechLimitMode = "time"; menu.speechMinutes = 1;
                    originalPosition = menu.position;
                    const reader = find(menu, "reader-page-text");
                    input.parent = reader; reader.forceActiveFocus();
                    input.keyClick(Qt.Key_Space);
                    if (!menu.speechActive || menu.position !== originalPosition) throw Error("Space did not start narration without page turning");
                    originalDeadline = menu.speechDeadline;
                    space(false);
                    if (!menu.speechPaused) throw Error("Space did not pause");
                    space(true);
                    if (!menu.speechPaused) throw Error("Held Space toggled playback");
                    hold = 0; phase++; return;
                }
                if (phase === 2) {
                    if (++hold < 10) return;
                    // Even if a fast test utterance completes, no next page starts.
                    if (!menu.speechPaused || menu.position !== originalPosition) throw Error("Paused reader advanced");
                    space(false);
                    if (menu.speechPaused || menu.speechDeadline - originalDeadline < 900) throw Error("Resume did not preserve remaining timer time");
                    phase++; return;
                }
                if (phase === 3) {
                    if (menu.position === originalPosition || menu.speechAdvancing) return;
                    menu.stopSpeech(); hold = 0; phase++; return;
                }
                if (phase === 4) {
                    if (++hold < 4) return;
                    menu.speechLimitMode = "none";
                    space(false); phase++; return;
                }
                if (phase === 5) {
                    if (!menu.speechAdvancing) return;
                    space(false); originalPosition = menu.position; hold = 0; phase++; return;
                }
                if (phase === 6) {
                    if (++hold < 8 || menu.busy) return;
                    if (!menu.speechPaused || !menu.speechAdvancing) throw Error("Pause between pages did not hold the session");
                    space(false); phase++; return;
                }
                if (phase === 7) {
                    if (menu.speechAdvancing) return;
                    menu.stopSpeech();
                    if (menu.speechPaused || menu.speechDeadline) throw Error("Stop retained paused state");
                    menu.readingMode = false;
                    space(false);
                    if (menu.speechActive) throw Error("Space started voice outside reader mode");
                    console.log("PASS: Space starts/pauses/resumes without page turns, ignores repeats, holds page transitions and timer, Stop clears pause");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
