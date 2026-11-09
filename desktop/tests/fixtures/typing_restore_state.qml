import QtQuick
import Quickshell
ShellRoot {
    property var menu: null
    property string book: ""
    property int savedPosition: 0
    property string savedInput: ""
    PanelWindow { id: panel; implicitWidth: 640; implicitHeight: 600 }
    Component { id: factory; TypingMenu { anchors.fill: parent } }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const found = find(child, name); if (found) return found; }
        return null;
    }
    Timer {
        interval: 200; running: true; repeat: true
        property int phase: 0
        property int ticks: 0
        property int wait: 0
        onTriggered: {
            try {
                if (++ticks > 200) throw Error("Reader restore timed out at phase " + phase);
                if (phase === 0) { menu = factory.createObject(panel.contentItem); phase++; return; }
                if (phase === 1) {
                    if (!menu.readerStateLoaded) return;
                    menu.send({action: "add", title: "Restore fixture", text: "A durable book remembers its reading position and settings. ".repeat(100)});
                    phase++; return;
                }
                if (phase === 2) {
                    if (menu.busy || !menu.bookId) return;
                    book = menu.bookId;
                    menu.readingMode = true; menu.fullscreen = true;
                    menu.speechProfile = "kokoro-sarah"; menu.speechRate = 1.25;
                    menu.speechLimitMode = "chapters"; menu.speechChapterCount = 3; menu.speechMinutes = 22;
                    menu.notebookFilter = "Plot";
                    menu.seek(137); phase++; return;
                }
                if (phase === 3) {
                    if (menu.busy) return;
                    savedPosition = menu.position;
                    menu.visible = false; wait = 0; phase++; return;
                }
                if (phase === 4) {
                    if (++wait < 4) return;
                    menu.destroy(); menu = null; phase++; return;
                }
                if (phase === 5) { menu = factory.createObject(panel.contentItem); menu.reopen(); phase++; return; }
                if (phase === 6) {
                    if (!menu.readerStateLoaded || menu.busy || !menu.bookId) return;
                    if (!menu.readingMode || !menu.fullscreen || menu.speechProfile !== "kokoro-sarah" || menu.speechRate !== 1.25 || menu.speechLimitMode !== "chapters" || menu.speechChapterCount !== 3 || menu.speechMinutes !== 22 || menu.notebookFilter !== "Plot") throw Error("Reader preferences did not survive recreation");
                    if (!menu.practicing || menu.bookId !== book || menu.position !== savedPosition) throw Error("Book/page did not restore");
                    if (menu.speaking || menu.speechDeadline || menu.readerMenu.visible) throw Error("Transient playback/UI restarted");
                    menu.showLibrary(); menu.visible = false; wait = 0; phase++; return;
                }
                if (phase === 7) {
                    if (++wait < 4) return;
                    menu.visible = true; menu.reopen();
                    if (menu.practicing) throw Error("Same-instance reopen lost library view");
                    menu.visible = false; menu.destroy(); menu = null; phase++; return;
                }
                if (phase === 8) { menu = factory.createObject(panel.contentItem); menu.reopen(); phase++; return; }
                if (phase === 9) {
                    if (!menu.readerStateLoaded || menu.busy || !menu.bookId) return;
                    if (menu.practicing || menu.position !== savedPosition) throw Error("Library view was not restored after recreation");
                    menu.goBack(); menu.readingMode = false; menu.send({action: "open", id: book}); phase++; return;
                }
                if (phase === 10) {
                    if (menu.busy) return;
                    savedInput = menu.passage.slice(0, 8);
                    find(menu, "typing-input").text = savedInput;
                    menu.saveProgress(); menu.visible = false; wait = 0; phase++; return;
                }
                if (phase === 11) {
                    if (++wait < 4) return;
                    menu.destroy(); menu = null; phase++; return;
                }
                if (phase === 12) { menu = factory.createObject(panel.contentItem); menu.reopen(); phase++; return; }
                if (phase === 13) {
                    if (!menu.readerStateLoaded || menu.busy || !menu.bookId) return;
                    if (menu.readingMode || !menu.practicing || find(menu, "typing-input").text !== savedInput || menu.position !== savedPosition) throw Error("Typed input/view did not restore");
                    console.log("PASS: fresh-instance reader preferences, book/page, library view, same-instance reopen and typed input restore; no automatic playback");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
