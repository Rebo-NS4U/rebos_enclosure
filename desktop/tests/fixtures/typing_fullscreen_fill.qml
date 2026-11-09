import QtQuick
import Quickshell
ShellRoot {
    PanelWindow {
        id: window
        implicitWidth: 640; implicitHeight: 260
        TypingMenu { id: menu; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const found = find(child, name); if (found) return found; }
        return null;
    }
    Timer {
        interval: 100; repeat: true; running: true
        property int phase: 0
        property int ticks: 0
        property int hold: 0
        property int originalPosition: 0
        property int originalRevision: 0
        property int compactWords: 0
        onTriggered: {
            try {
                if (++ticks > 150) throw Error("Fullscreen fill timed out at phase " + phase);
                if (phase === 0) {
                    menu.readingMode = true; menu.practicing = true;
                    menu.send({action: "add", title: "Fullscreen buffer", text: "The story carries on with enough words to fill every available line on the screen. ".repeat(200)});
                    phase++; return;
                }
                if (phase === 1) {
                    if (menu.busy || !menu.bookId || ++hold < 6) return;
                    originalPosition = menu.position; originalRevision = menu.bookRevision;
                    compactWords = menu.passage.length;
                    window.implicitHeight = 1080; window.implicitWidth = 1280; menu.fullscreen = true;
                    hold = 0; phase++; return;
                }
                const reader = find(menu, "reader-page-text");
                if (phase === 2) {
                    if (++hold < 8) return;
                    if (menu.position !== originalPosition || menu.bookRevision !== originalRevision) throw Error("Fullscreen changed the bookmark");
                    if (menu.passage.length <= compactWords || menu.pageLayout.lines < 12) throw Error("Fullscreen retained only a few lines: " + menu.pageLayout.lines + " loaded=" + menu.pageSource.length);
                    if (reader.contentHeight > reader.height || reader.contentHeight < reader.height - 3 * menu.readerLineHeight) throw Error("Fullscreen did not fill the reading area: " + reader.contentHeight + "/" + reader.height);
                    menu.fullscreen = false; window.implicitHeight = 260; window.implicitWidth = 640;
                    hold = 0; phase++; return;
                }
                if (phase === 3) {
                    if (++hold < 6) return;
                    menu.fullscreen = true; window.implicitHeight = 1080; window.implicitWidth = 1280;
                    menu.send({action: "open", id: menu.bookId});
                    hold = 0; phase++; return;
                }
                if (phase === 4) {
                    if (menu.busy || ++hold < 8) return;
                    if (reader.contentHeight > reader.height || reader.contentHeight < reader.height - 3 * menu.readerLineHeight) throw Error("Fullscreen reopening did not fill its first page");
                    console.log("PASS: compact-to-fullscreen and fullscreen reopening fill the viewport without navigation or bookmark changes");
                    Qt.quit();
                }
            } catch (error) { console.error("FAIL:", error); Qt.exit(1); }
        }
    }
}
