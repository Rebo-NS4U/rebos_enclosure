import QtQuick
import QtQuick.Window
import QtTest as TestTools
import Quickshell
ShellRoot {
    Window {
        visible: true; width: 800; height: 640
        TypingMenu { id: practice; anchors.fill: parent }
        TestTools.TestCase { id: driver; name: "CorrectFeedback"; when: false }
    }
    Timer {
        interval: 200; running: true; repeat: true
        property int phase: 0
        onTriggered: {
            try {
                if (phase++ === 0) {
                    practice.practicing = true;
                    practice.pageSource = "abc words to type. ".repeat(20);
                    practice.fitPage(); practice.focusPassage(); return;
                }
                for (const key of [Qt.Key_A, Qt.Key_B, Qt.Key_C]) driver.keyClick(key, Qt.NoModifier, 0);
                for (let i = 0; i < 3; i++) {
                    const glyph = practice.glyphItems[i];
                    if (glyph.rotation || glyph.scale !== 1 || glyph.transform[0].x || glyph.transform[0].y) throw Error("Correct letter moved like a rejection: " + i);
                    if (!glyph.typed || glyph.incorrect || glyph.failedFeedback) throw Error("Correct letter rejected: " + i);
                }
                const failures = practice.failureEvents;
                const correct = practice.glyphItems[0];
                // Modifier/navigation keys must not change input or replay rejection.
                driver.keyClick(Qt.Key_Meta, Qt.NoModifier, 0);
                driver.keyClick(Qt.Key_Left, Qt.NoModifier, 0);
                driver.keyClick(Qt.Key_Right, Qt.NoModifier, 0);
                practice.requestFeedback("error", correct);
                correct.startFeedback(true);
                if (correct.failedFeedback || correct.rejectionOffset || correct.rotation || correct.scale !== 1)
                    throw Error("Correct glyph accepted stale rejection feedback");
                if (practice.failureEvents !== failures) throw Error("Stale rejection counted as an error");
                if (practice.failureEvents) throw Error("Correct keys triggered error events: " + practice.failureEvents);
                driver.keyClick(Qt.Key_X, Qt.NoModifier, 0);
                if (!practice.glyphItems[3].failedFeedback) throw Error("Mistake did not animate");
                console.log("PASS: correct keystrokes avoid rejection and incorrect input animates");
                Qt.quit();
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
