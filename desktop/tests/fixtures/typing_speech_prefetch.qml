import QtQuick
import Quickshell
ShellRoot {
    PanelWindow {
        implicitWidth: 640; implicitHeight: 480
        TypingMenu { id: menu; anchors.fill: parent }
    }
    Timer {
        interval: 50; running: true; repeat: true
        property int phase: 0
        property int ticks: 0
        property int hold: 0
        property int nextPosition: 0
        property string expectedText: ""
        onTriggered: {
            try {
                if (++ticks > 500) throw Error("Prefetch timed out in phase " + phase);
                if (phase === 0) {
                    menu.readingMode = true;
                    menu.send({action: "add", title: "Lookahead", text: "Chapter 1\n\n" + "A calm voice tells the story. ".repeat(90) + "\n\nAnother paragraph with a different rhythm. ".repeat(40)});
                    phase++; return;
                }
                if (phase === 1) {
                    if (menu.busy || !menu.bookId || ++hold < 6) return;
                    menu.toggleSpeech(); phase++; return;
                }
                if (phase === 2) {
                    if (!menu.speechPrefetchReady) return;
                    if (menu.position !== 0 || menu.busy) throw Error("Lookahead moved the visible page");
                    nextPosition = menu.speechPageEnd;
                    expectedText = menu.speechPrefetchText;
                    if (!expectedText.length || expectedText === menu.speechText) throw Error("Next page was not prepared");
                    phase++; return;
                }
                if (phase === 3) {
                    if (menu.position === 0 || menu.speechAdvancing || menu.busy) return;
                    if (menu.position !== nextPosition || menu.speechText !== expectedText) throw Error("Prepared page differs from the spoken next page");
                    menu.stopSpeech(); hold = 0; phase++; return;
                }
                if (phase === 4) {
                    if (++hold < 8) return;
                    if (menu.speaking || menu.speechPrefetchRequest !== -1 || menu.speechPrefetchReady) throw Error("Stop did not cancel lookahead");
                    menu.speechAutoAdvance = false; menu.toggleSpeech(); hold = 0; phase++; return;
                }
                if (phase === 5) {
                    if (++hold < 6) return;
                    if (menu.speechPrefetchRequested) throw Error("Bounded reading preloaded an unwanted page");
                    menu.stopSpeech();
                    console.log("PASS: next-page speech preloads without moving progress, matches measured layout, and cancels on Stop");
                    Qt.quit();
                }
            } catch (error) { console.error("FAIL:", error); Qt.exit(1); }
        }
    }
}
