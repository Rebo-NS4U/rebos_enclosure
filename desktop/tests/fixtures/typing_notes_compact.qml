import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
ShellRoot {
    PanelWindow {
        visible: true
        implicitWidth: 960; implicitHeight: 720
        Item { id: compactAnchor; width: 640; height: 180 }
        TypingMenu { id: practice; anchors.fill: parent; menuAnchorItem: compactAnchor }
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
                    practice.wordTools.grabFocus = false; // QtTest has no native Wayland input serial.
                    practice.send({action: "add", title: "Notebook test", text: "Words for a notebook. ".repeat(80)});
                    phase++; return;
                }
                if (practice.busy || practice.noteSaving || !practice.bookId) return;
                if (phase === 1) { practice.openNotebook(); phase++; return; }
                if (phase === 2) {
                    if (!practice.notebookBrowsing || panel.width > 640 || panel.height > 480) throw Error("Browser bounds incorrect");
                    if (panel.anchor.item !== compactAnchor || panel.anchor.rect.x !== 0 || panel.anchor.rect.y !== compactAnchor.height + 6) throw Error("Compact notes lost their original position");
                    if (panel.surface.variant !== "popup") throw Error("Notes do not use the themed popup surface");
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
                    find(panel.contentItem, "typing-notes-sheet").grabToImage(result => result.saveToFile("/tmp/enclosure-notes-top.png"));
                    editor.text = "A careful observer.";
                    editor.forceActiveFocus();
                    const save = find(panel.contentItem, "typing-save-word-note");
                    const pos = save.mapToItem(panel.contentItem, 0, 0);
                    if (!panel.visible || pos.y < 0 || pos.y + save.height > panel.height || panel.height < 400) throw Error("Save is clipped by compact parent");
                    keys.mouseClick(save, save.width / 2, save.height / 2);
                    phase++; return;
                }
                if (phase === 4) {
                    if (practice.editingWordNote || practice.savedWordNote !== "A careful observer.") throw Error("Save button did not save note");
                    practice.openNotebook(); phase++; return;
                }
                if (phase === 5) {
                    if (practice.noteEntries.length !== 1) return;
                    search.text = "observer";
                    if (practice.visibleNoteEntries.length !== 1) throw Error("Content search failed");
                    practice.notebookFilter = "Plot";
                    if (practice.visibleNoteEntries.length) throw Error("Section filtering failed");
                    practice.notebookFilter = "People";
                    phase++; return;
                }
                if (phase === 6) {
                    const card = find(panel.contentItem, "typing-notebook-entry-elliot");
                    if (!card || card.height > 100) throw Error("Compact note card missing or too tall");
                    keys.mouseClick(card, card.width / 2, card.height / 2, Qt.LeftButton, Qt.NoModifier, 50); phase++; return;
                }
                if (phase === 7) {
                    if (!practice.noteLoaded) return;
                    const edit = find(panel.contentItem, "typing-edit-word-note");
                    keys.mouseClick(edit, edit.width / 2, edit.height / 2);
                    editor.text = "Unsaved draft";
                    const cancel = find(panel.contentItem, "typing-cancel-note-edit");
                    keys.mouseClick(cancel, cancel.width / 2, cancel.height / 2);
                    if (editor.text !== "A careful observer." || practice.noteDirty) throw Error("Cancel lost saved note");
                    console.log("PASS: compact notes bounds, pinned search, create, mouse save, search/filter, dense cards, cancel");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
