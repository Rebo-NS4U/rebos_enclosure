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
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    function count(item) {
        let n = 1;
        for (const child of item.children || []) n += count(child);
        return n;
    }
    Timer {
        interval: 16; running: true; repeat: true
        property int step: 0
        property int cycles: 0
        property int frames: 0
        property int baseline: 0
        property double previous: Date.now()
        property real earlyTime: 0
        property real lateTime: 0
        onTriggered: {
            try {
                const now = Date.now(), gap = now - previous; previous = now;
                if (step++ === 0) { practice.practicing = true; return; }
                if (step < 25) return;
                const input = find(practice, "typing-input");
                if (frames === 0) {
                    practice.restoring = true;
                    input.text = "";
                    practice.pageSource = "Window " + cycles + ": Some words to type with animated transitions. ".repeat(120);
                    practice.fitPage();
                    practice.restoring = false;
                    practice.focusPassage(); practice.refreshPageCaret();
                } else {
                    input.insert(input.length, practice.passage.charAt(input.length));
                    if (cycles < 10) earlyTime += gap;
                    if (cycles >= 70) lateTime += gap;
                    if (frames === 18) {
                        const offset = practice.pageLayout.words.find(word => word.line >= 5).start;
                        practice.restoring = true;
                        input.text = practice.passage.slice(0, offset);
                        input.cursorPosition = input.length;
                        practice.restoring = false;
                        practice.refreshPageCaret();
                        practice.requestFeedback("line", practice.glyphItems[offset]);
                    }
                }
                if (++frames === 24) {
                    const objects = count(practice);
                    if (!cycles) baseline = objects;
                    if (objects > baseline * 1.3) throw Error("Retained visual objects grew: " + baseline + " -> " + objects);
                    if (practice.activeEffects > 13) throw Error("Effects exceeded bound");
                    if (++cycles === 80) {
                        const status = JSON.parse(practice.status());
                        if (status.animationTiming.frames <= 0 || status.glyphCount > 900 || status.loadedCharacters > 8192)
                            throw Error("Missing or unbounded performance status");
                        console.log("TIMING:", JSON.stringify(status.animationTiming));
                        console.log("PASS: 80 window rebuilds, 1840 keys; objects", baseline, objects, "early/late ms", earlyTime, lateTime);
                        Qt.quit(); return;
                    }
                    frames = 0;
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
