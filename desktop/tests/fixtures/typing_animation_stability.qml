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
    Timer {
        interval: 16; running: true; repeat: true
        property int step: 0
        property int frames: 0
        property int cycles: 0
        property real baseline: 0
        onTriggered: {
            try {
                if (step++ === 0) {
                    practice.practicing = true;
                    practice.pageSource = "Some words to type with animated row transitions. ".repeat(120);
                    practice.fitPage(); return;
                }
                if (step < 25) return;
                const input = find(practice, "typing-input");
                const scroll = find(practice, "typing-page-visuals");
                if (frames === 0) {
                    const offset = practice.pageLayout.words.find(word => word.line >= 3 + cycles % 20).start;
                    practice.restoring = true;
                    input.text = practice.passage.slice(0, offset);
                    input.cursorPosition = input.length;
                    practice.restoring = false;
                    practice.refreshPageCaret();
                    practice.focusPassage();
                    baseline = scroll.contentY;
                    practice.requestFeedback("line", practice.glyphItems[offset]);
                } else if (Math.abs(scroll.contentY - baseline) > 0.1) {
                    throw Error("Row animation moved viewport: " + baseline + " -> " + scroll.contentY);
                }
                if (++frames > 48) {
                    if (practice.activeEffects !== 0) throw Error("Animation did not settle");
                    if (Object.keys(practice.glyphItems).length > 900) throw Error("Glyph registry grew beyond viewport");
                    frames = 0;
                    if (++cycles === 30) { console.log("PASS: 30 row animations keep viewport stable, glyphs bounded, and effects settled"); Qt.quit(); }
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
