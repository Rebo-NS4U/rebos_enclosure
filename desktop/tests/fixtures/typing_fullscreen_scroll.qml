import QtQuick
import Quickshell
ShellRoot {
    PanelWindow {
        implicitWidth: 960; implicitHeight: 700
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
        property real readerX: 0
        property int bookmark: 145
        onTriggered: {
            try {
                const input = find(menu, "typing-input");
                if (step === 0) {
                    menu.practicing = true; menu.fullscreen = true; menu.readingMode = true;
                    menu.position = bookmark;
                    menu.pageSource = "A gentle morning with words to read and type. ".repeat(200);
                    menu.paragraphStarts = [440, 880, 1320]; menu.fitPage();
                } else if (step === 1) {
                    readerX = find(menu, "reader-page-text").positionToRectangle(0).x;
                    menu.readingMode = false; menu.fitPage();
                } else if (step === 2) {
                    const text = find(menu, "fullscreen-typing-text");
                    if (!text.visible || text.font.pixelSize !== find(menu, "reader-page-text").font.pixelSize)
                        throw Error("Typing does not share reader typography");
                    if (Math.abs(text.positionToRectangle(0).x - readerX) > 1)
                        throw Error("Typing paragraph indentation differs from reader");
                    menu.focusPassage();
                    const initialCaret = find(menu, "fullscreen-typing-caret");
                    if (!initialCaret || !initialCaret.visible || initialCaret.width < 1 || initialCaret.height < menu.readingFont.pixelSize)
                        throw Error("Initial typing caret missing");
                    if (!input.activeFocus || text.activeFocus) throw Error("Input focus belongs to wrong editor");
                    input.text = menu.passage.slice(0, Math.floor(menu.passage.length * 0.85));
                    input.cursorPosition = input.length;
                    menu.followFullscreenTyping();
                } else {
                    const scroll = find(menu, "fullscreen-typing-scroll");
                    const text = find(menu, "fullscreen-typing-text");
                    const caret = text.cursorRectangle;
                    const paintedCaret = find(menu, "fullscreen-typing-caret");
                    if (!paintedCaret.visible || paintedCaret.opacity <= 0 || paintedCaret.z <= 0
                            || Math.abs(paintedCaret.x - caret.x) > 0.1 || Math.abs(paintedCaret.y - caret.y) > 0.1)
                        throw Error("Visible caret did not follow typed input");
                    if (scroll.contentY <= 0 || caret.y < scroll.contentY || caret.y + caret.height > scroll.contentY + scroll.height)
                        throw Error("Continuous typing did not scroll the caret into view");
                    if (menu.position !== bookmark || menu.pageTransitions !== 0)
                        throw Error("Scrolling changed bookmark or turned a page");
                    if (!/[\n\u2029]/.test(text.getText(0, text.length))) throw Error("Paragraphs missing");
                    console.log("PASS: fullscreen typing matches reader font and indentation, preserves paragraphs and scrolls with a visible caret while input retains focus");
                    Qt.quit();
                }
                step++;
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
