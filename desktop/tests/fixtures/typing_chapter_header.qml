import QtQuick
import QtQuick.Window
import Quickshell
import qs.modules.theme
ShellRoot {
    Window {
        visible: true
        id: driver
        width: 640; height: 600
        color: Colors.surface
        TypingMenu { id: practice; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        interval: 500; running: true; repeat: true
        property int phase: 0
        onTriggered: {
            try {
                if (phase === 0) {
                    practice.practicing = true;
                    practice.bookTitle = "A book to practice";
                    practice.chapters = [{title: "The quiet beginning", position: 0}, {title: "A new discovery", position: 1000}];
                    practice.bookLength = 2000;
                    practice.pageSource = "A gentle morning with words to read and type. ".repeat(100);
                    practice.fitPage(); phase++; return;
                }
                const card = find(practice, "typing-chapter-card");
                const highlight = find(practice, "typing-line-highlight");
                const scroll = find(practice, "typing-page-visuals");
                const title = find(practice, "typing-chapter-card-title");
                const input = find(practice, "typing-input");
                if (phase === 1) {
                    if (!card.visible || card.height < 48) throw Error("Opening card missing");
                    input.text = practice.passage.slice(0, 1);
                    phase++; return;
                }
                if (phase === 2) {
                    if (card.visible) throw Error("Card stayed visible after typing began");
                    practice.position = 100; input.text = "";
                    phase++; return;
                }
                if (phase === 3) {
                    if (card.visible) throw Error("Card returned mid-chapter");
                    practice.position = 1000;
                    phase++; return;
                }
                if (phase === 4) {
                    if (!card.visible || title.text !== "A new discovery") throw Error("New chapter opening card missing");
                    if (card.variant !== "pane" || card.styleOverride !== "") throw Error("Card bypasses theme");
                    console.log("PASS: small chapter card hides on typing, stays hidden mid-chapter, returns at next chapter");
                }
                Qt.quit();
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
