import QtQuick
import QtQuick.Window
import Quickshell
import qs.config
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
        interval: 40; running: true; repeat: true
        property int phase: 0
        property int ticks: 0
        onTriggered: {
            try {
                const input = find(practice, "typing-input");
                const tab = practice.glyphItems[0];
                const ret = practice.glyphItems[1];
                if (phase === 0) {
                    practice.practicing = true;
                    practice.pageSource = "\t\n\tWords to type. ".repeat(20);
                    practice.fitPage(); practice.focusPassage(); phase++; return;
                }
                if (phase === 1) {
                    practice.handleWhitespaceKey({key: Qt.Key_Tab, text: "", modifiers: 0});
                    if (!tab.spark || tab.failedFeedback) throw Error("Correct Tab did not animate");
                    phase++; return;
                }
                if (phase === 2) {
                    if (!(tab.formattingMotionX > 0) || tab.formattingMotionY !== 0) throw Error("Tab did not slide forward");
                    practice.handleWhitespaceKey({key: Qt.Key_Return, text: "", modifiers: 0});
                    if (!ret.spark || ret.failedFeedback) throw Error("Correct Return did not animate");
                    phase++; return;
                }
                if (phase === 3) {
                    if (!(ret.formattingMotionX < 0) || !(ret.formattingMotionY > 0)) throw Error("Return did not hook down and left");
                    if (practice.activeEffects > 13) throw Error("Feedback exceeded shared budget");
                    phase++; return;
                }
                if (phase === 4) {
                    if (++ticks < 12) return;
                    if (tab.spark || ret.spark || tab.formattingMotionX || ret.formattingMotionY) throw Error("Key motion did not settle");
                    for (let index = 0; index < 30; index++) {
                        input.text = ""; input.cursorPosition = 0;
                        practice.handleWhitespaceKey({key: Qt.Key_Tab, text: "", modifiers: 0});
                        practice.handleWhitespaceKey({key: Qt.Key_Return, text: "", modifiers: 0});
                    }
                    if (practice.activeEffects > 13 || input.text !== "\t\n") throw Error("Rapid formatting keys exceeded effect cap or lost input");
                    input.text = "x"; input.cursorPosition = input.length;
                    if (!tab.failedFeedback) throw Error("Mistyped Tab lost error animation");
                    Config.animDuration = 0;
                    if (practice.activeEffects || tab.spark) throw Error("Motion off did not stop effects");
                    input.text = ""; input.cursorPosition = 0;
                    practice.handleWhitespaceKey({key: Qt.Key_Tab, text: "", modifiers: 0});
                    practice.handleWhitespaceKey({key: Qt.Key_Return, text: "", modifiers: 0});
                    if (tab.spark || ret.spark || practice.activeEffects) throw Error("Reduced motion animated formatting");
                    console.log("PASS: Tab slide, Return hook, settle, error feedback, shared cap, reduced motion");
                    phase = 5; running = false; Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
