import QtQuick
import Quickshell
import qs.modules.bar.layouts
import qs.modules.shell
import qs.modules.theme
ShellRoot {
    id: harness
    property bool closeRequested: false
    PanelWindow {
        implicitWidth: 640
        implicitHeight: 500
        color: "transparent"
        TypingMenu { id: practice; anchors.fill: parent; onBackRequested: harness.closeRequested = true }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (let child of item.children ?? []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        property int phase: 0
        property int expectedPosition: 0
        interval: Math.max(900, Motion.base * 1.5)
        running: true
        repeat: true
        onTriggered: {
            try {
                if (phase === 0) {
                    const bar = Qt.createComponent("modules/bar/layouts/IslandBar.qml");
                    if (bar.status === Component.Error) throw Error(bar.errorString());
                    const panel = Qt.createComponent("modules/shell/UnifiedShellPanel.qml");
                    if (panel.status === Component.Error) throw Error(panel.errorString());
                    practice.loadPreset(0); practice.start(); phase++; return;
                }
                if (practice.busy || !practice.passage.length) return;
                if (practice.practicing && (practice.characters(practice.passage).length > 90 || practice.implicitHeight !== 240)) throw Error("Practice is not compact");
                const input = find(practice, "typing-input");
                const first = find(practice, "typing-character-0");
                if (!input || !first) throw Error("Typing input or glyph missing");
                if (phase === 1) {
                    if (Math.abs(first.opacity - 0.28) > 0.001) throw Error("Faint initial glyph missing");
                    input.text = practice.passage[0];
                } else if (phase === 2) {
                    if (first.opacity !== 1) throw Error("Typed glyph did not become opaque after animation");
                    practice.openBook(practice.bookId);
                } else if (phase === 3) {
                    if (input.text !== practice.passage[0]) throw Error("Partial typing progress did not resume");
                    input.text = "";
                } else if (phase < 100) {
                    if (phase === 4 && Math.abs(first.opacity - 0.28) > 0.001) throw Error("Backspace did not restore faint glyph");
                    if (practice.rounds < 1) { input.text = practice.passage; phase++; return; }
                    if (practice.position !== 0) throw Error("Continuous loop failed");
                    phase = 100;
                    practice.send({action: "add", title: "Unicode test", text: "😀 A gentle morning with words to type. ".repeat(8) + "\nChapter Two\nA new chapter begins here."});
                    return;
                } else if (phase === 100) {
                    if (first.text !== "😀") throw Error("Unicode glyph was split");
                    expectedPosition = practice.characters(practice.passage).length;
                    input.text = practice.passage;
                } else if (phase === 101) {
                    if (practice.position !== expectedPosition) throw Error("Unicode book position drifted");
                    if (practice.library.length < 2) throw Error("Library did not retain books");
                    practice.seek(practice.chapters[1].position);
                } else if (phase === 102) {
                    if (practice.chapterTitle !== "Chapter Two" || !practice.passage.startsWith("Chapter Two")) throw Error("Chapter navigation failed");
                    const slider = find(practice, "typing-book-position");
                    slider.value = Math.floor(practice.bookLength / 2);
                    slider.moved();
                } else if (phase === 103) {
                    if (practice.progress < 0.45 || practice.progress > 0.65) throw Error("Book position slider failed");
                    const place = practice.position;
                    find(practice, "typing-library").clicked();
                    if (practice.practicing) throw Error("Library button did not open library");
                    find(practice, "typing-back").clicked();
                    if (!practice.practicing || practice.position !== place || harness.closeRequested) throw Error("Back left typing or lost the current passage");
                    find(practice, "typing-library").clicked();
                    find(practice, "typing-import").clicked();
                } else if (phase === 104) {
                    if (!practice.filePickerActive) throw Error("File picker did not release panel input");
                } else if (phase === 105) {
                    if (practice.filePickerActive || practice.busy) return;
                    if (practice.bookTitle !== "picker test book" || practice.chapters.length !== 1) throw Error("Picker did not import the EPUB");
                    find(practice, "typing-back").clicked();
                    if (!practice.practicing || harness.closeRequested) throw Error("Back did not return to imported EPUB typing");
                    practice.openImport();
                } else if (phase === 106) {
                    if (!practice.filePickerActive) throw Error("Second picker did not open");
                } else {
                    if (practice.filePickerActive || practice.busy) return;
                    if (practice.bookTitle !== "picker test book") throw Error("Cancelling the picker changed the current book");
                    practice.goBack();
                    if (!practice.practicing || harness.closeRequested) throw Error("Back failed after cancelling the picker");
                    console.log("PASS: book paging, animations, saved progress, Unicode, chapter navigation, Back returns to typing, EPUB picker success and cancellation");
                    Qt.quit();
                }

                phase++;
            } catch (error) { console.error(error); Qt.quit(); }
        }
    }
}
