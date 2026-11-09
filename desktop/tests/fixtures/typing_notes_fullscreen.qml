import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
ShellRoot {
    PanelWindow {
        implicitWidth: 1600; implicitHeight: 1000
        TypingMenu { id: menu; anchors.fill: parent }
    }
    TestCase { id: input; when: false }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const found = find(child, name); if (found) return found; }
        return null;
    }
    function type(value) { for (const character of value) input.keyClick(character); }
    Timer {
        interval: 300; running: true; repeat: true
        property int phase: 0
        property int ticks: 0
        onTriggered: {
            try {
                if (++ticks > 100) throw Error("Fullscreen note test timed out in phase " + phase);
                if (phase === 0) {
                    menu.send({action: "add", title: "Fullscreen notes", text: "A book with a fullscreen notes editor. ".repeat(100)});
                    phase++; return;
                }
                if (menu.busy || menu.noteSaving || !menu.bookId) return;
                const panel = menu.wordTools;
                const title = find(panel.contentItem, "typing-word-term");
                const editor = find(panel.contentItem, "typing-word-note");
                const scroll = find(panel.contentItem, "typing-note-editor-scroll");
                if (phase === 1) {
                    if (!panel.grabFocus) throw Error("Notes popup does not request native focus by default");
                    // QtTest keys bypass Wayland and cannot provide a compositor
                    // input serial. Disable only this fixture's native popup grab.
                    panel.grabFocus = false;
                    menu.fullscreen = true; menu.readingMode = true;
                    menu.beginNotebookNote();
                    if (!panel.sideNotes || panel.anchor.rect.x < panel.anchor.item.width / 2 + 360 + 16 || panel.anchor.rect.x + panel.width > panel.anchor.item.width - 23 || panel.anchor.rect.y !== 24) throw Error("Fullscreen notes do not occupy the right margin clear of the reading column");
                    phase++; return;
                }
                if (phase === 2) {
                    input.parent = title;
                    input.mouseClick(title, title.width / 2, title.height / 2);
                    const reader = find(menu, "reader-page-text");
                    reader.focus = false;
                    menu.focusPassage(); // Same callback used after page loads and resizes.
                    if (reader.focus) throw Error("Reader refresh stole focus from the note title");
                    type("Focus note");
                    const create = find(panel.contentItem, "typing-new-notebook-note");
                    input.mouseClick(create, create.width / 2, create.height / 2);
                    phase++; return;
                }
                if (phase === 3) {
                    if (!menu.noteLoaded) return;
                    if (!editor.enabled || editor.height < scroll.availableHeight) throw Error("Fullscreen editor does not cover its visible input area: " + editor.height + " vs " + scroll.availableHeight);
                    find(panel.contentItem, "typing-cancel-note-edit").forceActiveFocus();
                    input.parent = editor;
                    input.mouseClick(scroll, scroll.availableWidth / 2, scroll.availableHeight - 20);
                    type("Fullscreen note text.");
                    if (!editor.activeFocus || editor.text !== "Fullscreen note text.") throw Error("Clicking the fullscreen typing area does not accept keyboard input");
                    input.keyClick(Qt.Key_Return);
                    type("Second line.");
                    input.keyClick(Qt.Key_S, Qt.ControlModifier);
                    phase++; return;
                }
                if (phase === 4) {
                    if (menu.editingWordNote || menu.savedWordNote !== "Fullscreen note text.\nSecond line.") throw Error("Fullscreen typed note did not save");
                    menu.openNotebookEntry("focus note"); phase++; return;
                }
                if (phase === 5) {
                    if (!menu.noteLoaded) return;
                    if (menu.savedWordNote !== "Fullscreen note text.\nSecond line.") throw Error("Reopened note lost typed text");
                    menu.openNotebook(); phase++; return;
                }
                if (phase === 6) {
                    input.parent = title;
                    input.mouseClick(title, title.width / 2, title.height / 2);
                    type("focus");
                    if (title.text !== "focus" || menu.visibleNoteEntries.length !== 1) throw Error("Fullscreen note search did not accept typing");
                    menu.openNotebookEntry("focus note"); phase++; return;
                }
                if (phase === 7) {
                    if (!menu.noteLoaded) return;
                    const edit = find(panel.contentItem, "typing-edit-word-note");
                    input.mouseClick(edit, edit.width / 2, edit.height / 2);
                    phase++; return;
                }
                if (phase === 8) {
                    editor.text += " Draft";
                    panel.visible = false;
                    menu.openNotebook();
                    if (!panel.opened || !menu.editingWordNote || !editor.text.endsWith(" Draft")) throw Error("Reopening notes lost an outside-dismissed draft");
                    editor.forceActiveFocus(); input.parent = editor; input.keyClick(Qt.Key_Escape);
                    if (panel.opened || !menu.fullscreen || !editor.text.endsWith(" Draft")) throw Error("Escape did not close notes while preserving fullscreen and draft");
                    menu.openNotebook();
                    if (!panel.opened || !editor.text.endsWith(" Draft")) throw Error("Escape lost the unsaved draft");
                    menu.cancelNoteEdit(); menu.openWord("story"); phase++; return;
                }
                if (phase === 9) {
                    if (!menu.noteLoaded) return;
                    if (panel.anchor.rect.x !== 24 || !panel.sideNotes || menu.notebookMode) throw Error("Lookup did not open on the left");
                    input.parent = find(panel.contentItem, "typing-notes-sheet"); panel.contentItem.forceActiveFocus(); input.keyClick(Qt.Key_Escape);
                    if (panel.opened || !menu.fullscreen) throw Error("Escape did not close lookup independently of fullscreen");
                    console.log("PASS: fullscreen notes on right, lookup on left, Escape closes both, typing/save and unsaved drafts preserved");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
