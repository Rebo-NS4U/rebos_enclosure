import QtQuick
import QtQuick.Window
import Quickshell
ShellRoot {
    Window {
        visible: true
        width: 960; height: 900
        TypingMenu { id: menu; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const found = find(child, name); if (found) return found; }
        return null;
    }
    function key(code, text) {
        const event = {key: code, text: text || "", modifiers: 0};
        return menu.handleWhitespaceKey(event) || menu.handleTypingEditKey(event);
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
                    key(Qt.Key_Space, " ");
                    if (input.text !== " " || !find(menu, "typing-character-0").incorrect) throw Error("Wrong indent was not recorded");
                    input.remove(0, input.length); input.cursorPosition = 0;
                    key(Qt.Key_Tab);
                    if (input.text !== "\t") throw Error("Tab was not captured");
                    const tab = find(menu, "typing-character-0");
                    if (tab.incorrect || !find(tab, "typing-keycap-0").visible) throw Error("Corrected Tab or keycap missing");
                    key(Qt.Key_Return);
                    if (input.text !== "\t\n" || !find(menu, "typing-character-1").incorrect) throw Error("Wrong Return was not recorded");
                    input.remove(1, input.length); input.cursorPosition = 1;
                    key(Qt.Key_Tab);
                    if (input.text !== "\t\t" || !find(menu, "typing-character-1").incorrect) throw Error("Wrong Tab was not recorded");
                    input.remove(1, input.length); input.cursorPosition = 1;
                    if (menu.currentWordItem().modelData.text !== "First") throw Error("Word lookup selected formatting instead of a word");
                    input.insert(input.length, "First paragraph."); input.cursorPosition = input.length;
                    const newlineIndex = input.length;
                    key(Qt.Key_Space, " ");
                    const newline = find(menu, "typing-character-" + newlineIndex);
                    if (!input.text.endsWith(" ") || !newline.incorrect) throw Error("Wrong newline was not recorded");
                    if (newline.width < menu.readingFont.pixelSize || !find(newline, "typing-keycap-" + newlineIndex).visible) throw Error("Return marker is too narrow or missing keycap");
                    input.remove(newlineIndex, input.length); input.cursorPosition = newlineIndex;
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
                console.log("PASS: wrong Tab/Return and whitespace recorded and corrected, keycaps render, reopen and mode roundtrip preserve input");
                Qt.quit();
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
