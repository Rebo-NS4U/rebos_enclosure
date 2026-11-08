import QtQuick
import Quickshell
import qs.modules.theme
ShellRoot {
    PanelWindow {
        id: driver
        implicitWidth: 640; implicitHeight: 600
        color: Colors.surface
        TypingMenu { id: practice; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        interval: 500; running: true; repeat: true
        property int phase: 0
        onTriggered: {
            try {
                if (phase === 0) {
                    practice.practicing = true;
                    practice.bookTitle = "A book to practice";
                    practice.chapters = [{title: "The quiet beginning", position: 0}, {title: "A new discovery", position: 1000}];
                    practice.bookLength = 2000;
                    practice.pageSource = "A gentle morning with words to read and type. ".repeat(100);
                    practice.fitPage(); phase++; return;
                }
                const card = find(practice, "typing-chapter-card");
                const highlight = find(practice, "typing-line-highlight");
                const scroll = find(practice, "typing-page-visuals");
                const title = find(practice, "typing-chapter-card-title");
                if (!card.visible || card.height < 48 || card.parent !== scroll.parent)
                    throw Error("Chapter card does not occupy the existing passage header space");
                const bottom = card.mapToItem(practice, 0, card.height).y;
                const rowTop = highlight.mapToItem(practice, 0, 0).y;
                if (bottom > rowTop || scroll.height !== 7 * practice.passageLineHeight)
                    throw Error("Chapter card overlaps the active row or expands its viewport");
                if (card.variant !== "pane" || card.styleOverride !== "") throw Error("Card bypasses the shared theme");
                if (phase === 1) {
                    practice.position = 100;
                    find(practice, "typing-input").text = practice.passage.slice(0, 200);
                    practice.refreshPageCaret(); phase++; return;
                }
                if (phase === 2 && (title.text !== "The quiet beginning" || practice.atChapterStart))
                    throw Error("Chapter card was not retained mid-chapter");
                if (phase === 2) { practice.position = 1000; phase++; return; }
                if (title.text !== "A new discovery") throw Error("Chapter card did not follow chapter changes");
                console.log("PASS: chapter header uses top space, persists, follows chapters, and inherits theme");
                Qt.quit();
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
