import QtQuick
import Quickshell
ShellRoot {
    PanelWindow {
        implicitWidth: 960; implicitHeight: 900
        TypingMenu { id: menu; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const found = find(child, name); if (found) return found; }
        return null;
    }
    function key(code, text) {
        return menu.handleWhitespaceKey({key: code, text: text || "", modifiers: 0});
    }
    Timer {
        interval: 400; running: true; repeat: true
        property int phase: 0
        property int polls: 0
        property string retained: ""
        property int savedRevision: 0
        onTriggered: {
            try {
                if (++polls > 50) throw Error("Whitespace fixture timed out");
                const input = find(menu, "typing-input");
                if (phase === 0) {
                    menu.fullscreen = true;
                    menu.send({action: "add", title: "Required whitespace", text: "First paragraph.\n\nSecond paragraph. " + "More words. ".repeat(300)});
                    phase++; return;
                }
                if (menu.busy) return;
                if (phase === 1) {
                    if (!menu.passage.startsWith("\tFirst paragraph.\n\n\tSecond")) throw Error("Formatted target missing");
                    if (!key(Qt.Key_Space, " ") || input.text.length) throw Error("Indent accepted a space");
                    key(Qt.Key_Tab);
                    if (input.text !== "\t") throw Error("Tab was not captured");
                    if (menu.currentWordItem().modelData.text !== "First") throw Error("Word lookup selected formatting instead of a word");
                    input.insert(input.length, "First paragraph."); input.cursorPosition = input.length;
                    if (!key(Qt.Key_Space, " ") || input.text.endsWith(" ")) throw Error("Paragraph accepted a space");
                    key(Qt.Key_Return); key(Qt.Key_Return); key(Qt.Key_Tab);
                    input.insert(input.length, "Sec"); input.cursorPosition = input.length;
                    retained = input.text;
                    if (retained !== "\tFirst paragraph.\n\n\tSec") throw Error("Required keys did not produce target prefix: " + JSON.stringify(retained));
                    menu.saveProgress(); savedRevision = menu.bookRevision;
                    menu.send({action: "open", id: menu.bookId}); phase++; return;
                }
                if (phase === 2) {
                    if (input.text !== retained || menu.progressConflict || menu.bookRevision !== savedRevision) throw Error("Reopen lost whitespace or revision");
                    const first = menu.pageLayout.words.find(word => word.text === "First");
                    const second = menu.pageLayout.words.find(word => word.text === "Second");
                    if (!first || !second || first.x !== menu.readingFont.pixelSize * 2 || second.line - first.line < 2)
                        throw Error("Indent or blank row was not rendered");
                    menu.toggleReadingMode(); phase++; return;
                }
                if (phase === 3) { menu.toggleReadingMode(); phase++; return; }
                if (input.text !== retained || menu.position !== 0 || menu.progressConflict) throw Error("Mode roundtrip lost partial progress");
                console.log("PASS: Tab and two Returns are required, indent and blank rows render, reopen and mode roundtrip preserve partial input and revision");
                Qt.quit();
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
