import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.modules.bar.layouts
import qs.modules.shell
import "TypingSpeed.js" as Speed
import qs.modules.theme
ShellRoot {
    id: harness
    property bool closeRequested: false
    PanelWindow {
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
        exclusionMode: ExclusionMode.Ignore
        mask: Region {}
        implicitWidth: 640
        implicitHeight: 600
        color: "transparent"
        TypingMenu { id: practice; anchors.fill: parent; onBackRequested: harness.closeRequested = true }
        Loader { id: freshView; anchors.fill: parent; active: false; visible: false; sourceComponent: TypingMenu {} }
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
                    let meter = Speed.record(Speed.create(), 1000);
                    meter = Speed.tick(meter, 2000, true);
                    if (Speed.rate(meter, 5, 2000) !== 60 || Speed.rate(meter, 0, 2000) !== 0) throw Error("WPM must count net correct five-character words");
                    const paused = Speed.pause(meter);
                    if (Speed.tick(paused, 9000, true).elapsed !== meter.elapsed || Speed.rate(meter, 5, 7000) !== 0) throw Error("WPM idle/pause handling failed");
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
                    if (!find(practice, "typing-caret-0").visible || Math.abs(first.opacity - 1) > 0.001) throw Error("Visible cursor block missing: " + JSON.stringify({opacity: first.opacity, current: first.caretHere, entrance: first.entrance, cursor: input.cursorPosition, practicing: practice.practicing, visible: find(practice, "typing-caret-0").visible, motion: Motion.base}));
                    if (Math.abs(find(practice, "typing-character-1").opacity - 0.28) > 0.001) throw Error("Upcoming text should stay faint");
                    input.text = practice.passage[0]; input.cursorPosition = input.length;
                } else if (phase === 2) {
                    if (Math.abs(first.opacity - 1) > 0.001) throw Error("Typed glyph did not become opaque after animation");
                    if (!find(practice, "typing-caret-1").visible) throw Error("Cursor did not advance");
                    input.cursorPosition = 0;
                    if (!find(practice, "typing-caret-0").visible) throw Error("Cursor does not follow editing position");
                    practice.openBook(practice.bookId);
                } else if (phase === 3) {
                    if (input.text !== practice.passage[0]) throw Error("Partial typing progress did not resume");
                    input.text = "";
                } else if (phase < 100) {
                    if (phase === 4 && (!find(practice, "typing-caret-0").visible || Math.abs(find(practice, "typing-character-1").opacity - 0.28) > 0.001)) throw Error("Backspace did not restore the cursor and faint text");
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
                    practice.showLibrary();
                    const chapters = find(practice, "typing-chapter-select");
                    if (chapters.currentIndex !== practice.currentChapterIndex || !chapters.displayText.length) throw Error("Chapter selection is not synchronized");
                    chapters.popup.open();
                } else if (phase === 102) {
                    const cards = find(practice, "typing-book-cards");
                    const card = cards.itemAtIndex(0);
                    if (!card || cards.count !== 1 || !find(card, "typing-card-progress").text.endsWith("%")) throw Error("Book cards invalid: " + JSON.stringify({count: cards.count, visible: cards.visible, height: cards.height, card: !!card, books: practice.libraryBooks.length, viewWidth: practice.width, viewHeight: practice.height, parentHeight: cards.parent.height, samples: practice.samplesExpanded}));
                    if (practice.samplesExpanded) throw Error("Practice samples should be collapsed by default");
                    const chapters = find(practice, "typing-chapter-select");
                    chapters.popup.contentItem.positionViewAtIndex(1, ListView.Contain);
                    const entry = chapters.popup.contentItem.itemAtIndex(1);
                    if (!entry || entry.text !== "Chapter Two") throw Error("Chapter popup is missing its labels");
                    entry.clicked();
                    phase = 110; return;
                } else if (phase === 110) {
                    if (practice.chapterTitle !== "Chapter Two" || !practice.passage.startsWith("Chapter Two") || !practice.practicing) throw Error("Chapter selection did not jump back to typing");
                    const slider = find(practice, "typing-book-position");
                    slider.value = Math.floor(practice.bookLength / 2);
                    slider.moved();
                    phase = 103; return;
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
                } else if (phase === 107) {
                    if (practice.filePickerActive || practice.busy) return;
                    if (practice.bookTitle !== "picker test book") throw Error("Cancelling the picker changed the current book");
                    practice.goBack();
                    if (!practice.practicing || harness.closeRequested) throw Error("Back failed after cancelling the picker");
                    input.text = practice.passage.slice(0, 3);
                    input.cursorPosition = input.length;
                    practice.saveProgress();
                    practice.visible = false;
                    freshView.active = true;
                    freshView.visible = true;
                    freshView.item.reopen();
                } else if (phase === 108) {
                    const restored = freshView.item;
                    if (restored.busy || !restored.bookId || restored.library.length < 3) return;
                    const restoredInput = find(restored, "typing-input");
                    if (!restored.practicing || restored.bookTitle !== "picker test book" || restoredInput.text !== restored.passage.slice(0, 3)) throw Error("A fresh view did not automatically resume the saved partial passage");
                    if (restored.libraryBooks.length !== 2 || restored.liveWpm !== 0) throw Error("Practice samples or restored text affect library/WPM");
                    console.log("PASS: automatic resume in a fresh view, book completion cards, secondary samples, live WPM, chapter navigation and EPUB picker");
                    Qt.quit();
                }

                phase++;
            } catch (error) { console.error(error); Qt.quit(); }
        }
    }
}
