import QtQuick
import Quickshell
import Quickshell.Wayland
ShellRoot {
    PanelWindow {
        implicitWidth: 640
        implicitHeight: 600
        color: "transparent"
        TypingMenu { id: practice; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        interval: 1200; running: true; repeat: true
        property int phase: 0
        onTriggered: {
            try {
                if (phase === 0) {
                    practice.practicing = true;
                    practice.restoring = true;
                    practice.pageSource = "A complete section with words to type. ".repeat(30);
                    practice.fitPage(); phase++; return;
                }
                const scroll = find(practice, "typing-page-visuals");
                const flow = find(practice, "typing-passage-flow");
                flow.forceLayout();
                if (practice.passage.length >= practice.pageSource.length || practice.pageLayout.lines > practice.layoutLineLimit) throw Error("Section was not bounded");
                if (scroll.height < 6 * practice.passageLineHeight || scroll.contentHeight <= scroll.height) throw Error("Expanded scrolling viewport missing");
                practice.restoring = false;
                const input = find(practice, "typing-input");
                input.text = practice.passage.slice(0, practice.passage.length - 10);
                input.cursorPosition = input.length;
                practice.refreshPageCaret();
                if (scroll.contentY <= 0) throw Error("Caret did not scroll down");
                input.cursorPosition = 0;
                practice.refreshPageCaret();
                if (scroll.contentY > 4) throw Error("Caret did not scroll back");
                console.log("PASS: bounded section, expanded viewport, cursor scrolling both ways"); Qt.quit();
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
