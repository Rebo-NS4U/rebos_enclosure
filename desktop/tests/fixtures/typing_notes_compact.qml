import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
ShellRoot {
    Window {
        visible: true
        width: 960; height: 720
        TypingMenu { id: practice; anchors.fill: parent }
    }
    TestCase { id: keys; when: false }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        interval: 300; running: true; repeat: true
        property int phase: 0
        property int ticks: 0
        onTriggered: {
            try {
                if (++ticks > 50) throw Error("Notes test timed out in phase " + phase);
                const panel = practice.wordTools;
                const search = find(panel.contentItem, "typing-word-term");
                const editor = find(panel.contentItem, "typing-word-note");
                if (phase === 0) {
                    practice.send({action: "add", title: "Notebook test", text: "Words for a notebook. ".repeat(80)});
                    phase++; return;
                }
                if (practice.busy || practice.noteSaving) return;
                if (phase === 1) { practice.openNotebook(); phase++; return; }
                if (phase === 2) {
                    if (!practice.notebookBrowsing || panel.width > 640 || panel.height > 480) throw Error("Browser bounds incorrect");
                    const scroll = find(panel.contentItem, "typing-word-scroll");
                    if (search.mapToItem(panel.contentItem, 0, 0).y >= scroll.mapToItem(panel.contentItem, 0, 0).y) throw Error("Search is not pinned above results");
                    practice.notebookFilter = "People";
                    find(panel.contentItem, "typing-new-notebook-note").clicked();
                    search.text = "Elliot";
                    find(panel.contentItem, "typing-new-notebook-note").clicked();
                    phase++; return;
                }
                if (phase === 3) {
                    if (!practice.noteLoaded) return;
                    if (!practice.editingWordNote || practice.noteCategory !== "People") throw Error("Creation did not enter categorized editor");
                    editor.text = "A careful observer.";
                    editor.forceActiveFocus();
                    keys.keyClick(Qt.Key_S, Qt.ControlModifier);
                    phase++; return;
                }
                if (phase === 4) {
                    if (practice.editingWordNote || practice.savedWordNote !== "A careful observer.") throw Error("Shortcut did not save note");
                    practice.openNotebook(); phase++; return;
                }
                if (phase === 5) {
                    if (practice.noteEntries.length !== 1) return;
                    search.text = "observer";
                    if (practice.visibleNoteEntries.length !== 1) throw Error("Content search failed");
                    practice.notebookFilter = "Plot";
                    if (practice.visibleNoteEntries.length) throw Error("Section filtering failed");
                    practice.notebookFilter = "People";
                    const card = find(panel.contentItem, "typing-notebook-entry-elliot");
                    if (!card || card.height > 100) throw Error("Compact note card missing or too tall");
                    practice.openNotebookEntry("elliot"); phase++; return;
                }
                if (phase === 6) {
                    if (!practice.noteLoaded) return;
                    find(panel.contentItem, "typing-edit-word-note").clicked();
                    editor.text = "Unsaved draft";
                    find(panel.contentItem, "typing-cancel-note-edit").clicked();
                    if (editor.text !== "A careful observer." || practice.noteDirty) throw Error("Cancel lost saved note");
                    console.log("PASS: compact notes bounds, pinned search, create, shortcut save, search/filter, dense cards, cancel");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
