import QtQuick
import Quickshell
ShellRoot {
    PanelWindow {
        implicitWidth: 640; implicitHeight: 480
        TypingMenu { id: menu; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const found = find(child, name); if (found) return found; }
        return null;
    }
    function move(key) { menu.readerKey({key: key, modifiers: Qt.ControlModifier}); }
    Timer {
        interval: 50; repeat: true; running: true
        property int phase: 0
        property int ticks: 0
        property int hold: 0
        property int target: 0
        property int pageEnd: 0
        property int originalPage: 0
        property double deadline: 0
        property string expectedText: ""
        onTriggered: {
            try {
                if (++ticks > 400) throw Error("Speech seek timed out at phase " + phase);
                if (phase === 0) {
                    menu.readingMode = true;
                    menu.send({action: "add", title: "Resume at word", text: "Alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec romeo sierra tango. ".repeat(70)});
                    phase++; return;
                }
                if (phase === 1) {
                    if (menu.busy || !menu.passage.length || ++hold < 10) return;
                    menu.speechLimitMode = "time"; menu.speechMinutes = 1;
                    menu.toggleSpeechPlayback(); phase++; return;
                }
                if (phase === 2) {
                    if (menu.speechHighlightStart < 0 || !menu.speechControlReady) return;
                    originalPage = menu.position; pageEnd = menu.speechPageEnd; deadline = menu.speechDeadline;
                    menu.toggleSpeechPlayback(); move(Qt.Key_L); move(Qt.Key_L);
                    target = menu.speechHighlightStart;
                    expectedText = menu.passage.slice(target).trim();
                    if (!menu.speechPaused || menu.speechSeekOffset !== target || target <= 0) throw Error("Paused word movement did not set the resume point");
                    menu.toggleSpeechPlayback(); phase++; return;
                }
                if (phase === 3) {
                    if (menu.speechRestartOffset >= 0 || menu.speechSourceOffset !== target || menu.speechHighlightStart < 0) return;
                    if (menu.speechText !== expectedText || menu.position !== originalPage || menu.speechPageEnd !== pageEnd) throw Error("Forward seek changed or repeated the page");
                    if (!menu.speechContinuous || menu.speechDeadline < deadline) throw Error("Seeking reset continuous reading or its timer");
                    menu.toggleSpeechPlayback(); move(Qt.Key_H);
                    target = menu.speechHighlightStart; expectedText = menu.passage.slice(target).trim();
                    menu.toggleSpeechPlayback(); phase++; return;
                }
                if (phase === 4) {
                    if (menu.speechRestartOffset >= 0 || menu.speechSourceOffset !== target || menu.speechHighlightStart < 0) return;
                    if (menu.speechText !== expectedText) throw Error("Backward seek resumed old audio");
                    menu.toggleSpeechPlayback(); menu.toggleSpeechPlayback();
                    if (!menu.speechControlReady || menu.speechRestartOffset >= 0 || menu.speechText !== expectedText) throw Error("Pause without word movement unnecessarily restarted audio");
                    phase++; return;
                }
                if (phase === 5) {
                    if (menu.position === originalPage || menu.busy || menu.speechAdvancing || menu.speechHighlightStart < 0) return;
                    if (menu.position !== pageEnd || menu.speechSourceOffset !== 0) throw Error("Seek broke exact next-page continuation");
                    menu.toggleSpeechPlayback(); move(Qt.Key_L); menu.toggleSpeechPlayback(); menu.stopSpeech(); hold = 0; phase++; return;
                }
                if (phase === 6) {
                    if (++hold < 12) return;
                    if (menu.speaking || menu.speechRestartOffset >= 0 || menu.speechSeekOffset >= 0 || menu.speechDeadline) throw Error("Stop allowed a pending seek to restart playback");
                    const reader = find(menu, "reader-page-text");
                    reader.select(0, 40); menu.toggleSpeechPlayback(); phase++; return;
                }
                if (phase === 7) {
                    if (menu.speechHighlightStart < 0) return;
                    menu.toggleSpeechPlayback(); move(Qt.Key_L); target = menu.speechHighlightStart;
                    menu.toggleSpeechPlayback(); phase++; return;
                }
                if (phase === 8) {
                    if (menu.speechRestartOffset >= 0 || menu.speechSourceOffset !== target || menu.speechHighlightStart < 0) return;
                    if (menu.speechContinuous || menu.speechText !== menu.passage.slice(target, 40).trim()) throw Error("Selected-text seek lost its bounded end");
                    menu.stopSpeech();
                    console.log("PASS: paused word movement resumes at the chosen word forward/backward, preserves timers and page continuation, keeps unchanged pauses exact, respects selection end and cancels pending seek on Stop");
                    Qt.quit();
                }
            } catch (error) { console.error("FAIL:", error); Qt.exit(1); }
        }
    }
}
