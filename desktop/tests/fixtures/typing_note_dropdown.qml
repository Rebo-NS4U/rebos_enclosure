import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
ShellRoot {
    PanelWindow {
        visible: true
        implicitWidth: 960; implicitHeight: 720
        Item { id: compactAnchor; width: 640; height: 180 }
        TypingMenu { id: menu; anchors.fill: parent; menuAnchorItem: compactAnchor }
    }
    TestCase { id: input; when: false }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        interval: 400; running: true; repeat: true
        property int step: 0
        property int ticks: 0
        onTriggered: {
            try {
                if (++ticks > 40) throw Error("Dropdown test timed out");
                if (step === 0) {
                    menu.wordTools.grabFocus = false; // QtTest has no native Wayland input serial.
                    menu.send({action: "add", title: "Dropdown test", text: "A book passage. ".repeat(100)}); step++; return; }
                if (menu.busy || !menu.bookId) return;
                if (step === 1) { menu.beginNotebookNote(); step++; return; }
                const select = find(menu.wordTools.contentItem, "typing-new-note-category");
                if (step === 2) { input.mouseClick(select, select.width / 2, select.height / 2); step++; return; }
                if (step === 3) {
                    if (!select.popup.visible) throw Error("Category dropdown did not open");
                    const list = select.popup.contentItem;
                    const window = list.Window.window;
                    const point = list.mapToItem(window.contentItem, 0, 0);
                    if (point.y < 0 || point.y + list.height > window.height + 1)
                        throw Error("Category options are clipped outside the notes window");
                    const row = list.itemAtIndex(1);
                    if (!row) throw Error("Category option missing");
                    input.mouseClick(row, row.width / 2, row.height / 2);
                    step++; return;
                }
                if (step === 4) {
                    if (menu.newNoteCategory !== "Settings" || select.popup.visible || menu.noteDropdownBottom !== 0) throw Error("Category click did not select and close");
                    find(menu.wordTools.contentItem, "typing-word-term").text = "A place";
                    find(menu.wordTools.contentItem, "typing-new-notebook-note").clicked();
                    step++; return;
                }
                if (step === 5) {
                    if (!menu.noteLoaded) return;
                    if (menu.noteCategory !== "Settings") throw Error("New note lost selected category");
                    console.log("PASS: New Note dropdown fits, mouse selection works, and creation retains category");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
