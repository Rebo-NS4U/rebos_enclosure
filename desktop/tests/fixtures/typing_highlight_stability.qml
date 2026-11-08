import QtQuick
import Quickshell
ShellRoot {
    PanelWindow {
        implicitWidth: 640
        implicitHeight: 600
        TypingMenu { id: practice; anchors.fill: parent }
    }
    property bool watching: false
    property int hiddenEvents: 0
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        interval: 16; running: true; repeat: true
        property int step: 0
        onTriggered: {
            try {
                if (step++ === 0) {
                    practice.practicing = true;
                    practice.pageSource = "Words to type without the row highlight flickering. ".repeat(100);
                    practice.fitPage(); return;
                }
                if (step < 25) return;
                const input = find(practice, "typing-input");
                const highlight = find(practice, "typing-line-highlight");
                const caret = find(practice, "typing-smooth-caret");
                if (!watching) {
                    practice.focusPassage(); practice.refreshPageCaret();
                    if (!highlight.visible) throw Error("Highlight was not initially visible");
                    highlight.visibleChanged.connect(() => { if (watching && !highlight.visible) hiddenEvents++; });
                    caret.visibleChanged.connect(() => { if (watching && !caret.visible) hiddenEvents++; });
                    watching = true;
                }
                if (hiddenEvents) throw Error("Highlight/caret disappeared during character handoff: " + hiddenEvents);
                if (step === 325) { console.log("PASS: highlight and caret stay visible through 300 character handoffs"); Qt.quit(); return; }
                input.insert(input.length, practice.passage.charAt(input.length));
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
