import QtQuick
import Quickshell
ShellRoot {
    PanelWindow {
        implicitWidth: 960; implicitHeight: 1000
        TypingMenu { id: menu; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const found = find(child, name); if (found) return found; }
        return null;
    }
    Timer {
        interval: 500; running: true; repeat: true
        property int step: 0
        property string retained: ""
        onTriggered: {
            try {
                const input = find(menu, "typing-input");
                const scroll = find(menu, "typing-page-visuals");
                const caret = find(menu, "typing-smooth-caret");
                if (step === 0) {
                    menu.practicing = true; menu.fullscreen = true; menu.position = 145;
                    menu.pageSource = "A gentle morning with words to read and type. ".repeat(300);
                    menu.fitPage(); menu.focusPassage();
                } else if (step === 1) {
                    if (!scroll.visible || scroll.height <= 7 * menu.passageLineHeight || menu.pageLineLimit <= 7)
                        throw Error("Fullscreen did not expand original typing viewport");
                    if (!caret.visible || !caret.targetGlyph || !input.activeFocus) throw Error("Original typing caret missing");
                    if (scroll.centerPadding !== 4) throw Error("Fullscreen wastes half its height on padding");
                    const offset = menu.pageLayout.words.find(word => word.line >= menu.pageLineLimit + 1).start;
                    input.text = menu.passage.slice(0, offset); input.cursorPosition = input.length;
                    retained = input.text; menu.refreshPageCaret();
                } else if (step === 2) {
                    if (!caret.visible || scroll.contentY <= 0) throw Error("Original cursor did not follow scrolling input");
                    const local = caret.mapToItem(scroll, 0, 0);
                    if (local.y < -1 || local.y + caret.height > scroll.height + 1) throw Error("Cursor outside viewport");
                    if (menu.position !== 145 || menu.pageTransitions) throw Error("Scrolling changed progress");
                    menu.fullscreen = false;
                } else {
                    if (scroll.height !== 7 * menu.passageLineHeight || !caret.visible || input.text !== retained)
                        throw Error("Compact typing or retained input changed: " + scroll.height + " vs " + (7 * menu.passageLineHeight) + " caret=" + caret.visible + " input=" + input.text.length + "/" + retained.length);
                    console.log("PASS: original animated glyph renderer and caret fill fullscreen, scroll with input and retain seven compact rows");
                    Qt.quit();
                }
                step++;
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
