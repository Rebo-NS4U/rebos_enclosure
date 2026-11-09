import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
ShellRoot {
    PanelWindow {
        implicitWidth: 640; implicitHeight: 480
        TypingMenu { id: menu; anchors.fill: parent }
    }
    TestCase { id: input; when: false }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        interval: 400; running: true; repeat: true
        property int phase: 0
        onTriggered: {
            try {
                if (phase === 0) {
                    menu.practicing = true; menu.readingMode = true;
                    menu.pageSource = "A cleaner reader with Nicole. ".repeat(100); menu.fitPage();
                } else if (phase === 1) {
                    const button = find(menu, "typing-reader-actions");
                    input.mouseClick(button, button.width / 2, button.height / 2);
                } else if (phase === 2) {
                    const settings = menu.readerMenu;
                    if (!settings.visible || !settings.opened) throw Error("Settings did not open");
                    if (find(settings.contentItem, "reader-voice-name").text !== "Voice") throw Error("Unexpected voice");
                    for (const name of ["reader-voice-select", "reader-voice-preview", "reader-speed", "reader-limit", "typing-mode", "typing-fullscreen", "typing-library", "reader-kokoro-setup"]) {
                        const control = find(settings.contentItem, name);
                        const point = control.mapToItem(settings.contentItem, 0, 0);
                        if (!control.visible || control.width <= 0 || point.y < 0 || point.y + control.height > settings.height || point.x < 0 || point.x + control.width > settings.width + 1) throw Error("Settings control clipped: " + name);
                    }
                    if (menu.speechRate !== 1.05) throw Error("Default speed is not faster");
                    const select = find(settings.contentItem, "reader-voice-select");
                    if (select.count !== 5 || select.currentText !== "Nicole") throw Error("Quality voice list/default incorrect");
                    input.mouseClick(select, select.width / 2, select.height / 2);
                } else if (phase === 3) {
                    const select = find(menu.readerMenu.contentItem, "reader-voice-select");
                    const list = select.popup.contentItem;
                    if (!select.popup.visible || list.mapToItem(menu.readerMenu.contentItem, 0, 0).y + list.height > menu.readerMenu.height) throw Error("Voice dropdown is clipped: y=" + list.mapToItem(menu.readerMenu.contentItem, 0, 0).y + " height=" + list.height + " window=" + menu.readerMenu.height);
                    const heart = list.itemAtIndex(1);
                    input.mouseClick(heart, heart.width / 2, heart.height / 2);
                } else if (phase === 4) {
                    if (!menu.readerMenu.visible) throw Error("Voice change dismissed settings");
                    if (menu.speechProfile !== "kokoro-heart") throw Error("Voice selection did not work");
                    find(menu.readerMenu.contentItem, "reader-voice-preview").clicked();
                    if (!menu.speaking || menu.speechContinuous) throw Error("Preview did not start bounded playback");
                    find(menu.readerMenu.contentItem, "reader-voice-preview").clicked();
                    const speed = find(menu.readerMenu.contentItem, "reader-speed");
                    input.mouseClick(speed, speed.width * 0.8, speed.height / 2);
                } else if (phase === 5) {
                    if (!menu.readerMenu.visible) throw Error("Speed change dismissed settings");
                    if (menu.speechRate <= 1.05) throw Error("Speed slider did not work");
                    const toggle = find(menu.readerMenu.contentItem, "reader-limit");
                    toggle.currentIndex = 1; toggle.activated(1);
                } else if (phase === 6) {
                    if (!menu.readerMenu.visible) throw Error("Reading-limit change dismissed settings");
                    if (menu.speechAutoAdvance) throw Error("Continuous reading toggle did not work");
                    const full = find(menu.readerMenu.contentItem, "typing-fullscreen");
                    input.mouseClick(full, full.width / 2, full.height / 2);
                } else if (phase === 7) {
                    if (!menu.fullscreen || !menu.readerMenu.visible) throw Error("Fullscreen change dismissed settings");
                    const mode = find(menu.readerMenu.contentItem, "typing-mode");
                    input.mouseClick(mode, mode.width / 2, mode.height / 2);
                } else if (phase === 8) {
                    if (menu.readingMode || !menu.readerMenu.visible) throw Error("Mode change dismissed settings");
                    const done = find(menu.readerMenu.contentItem, "reader-settings-close");
                    input.mouseClick(done, done.width / 2, done.height / 2);
                } else if (phase === 9) {
                    if (menu.readerMenu.visible) throw Error("Done did not dismiss settings");
                    menu.readerMenu.open();
                } else if (phase === 10) {
                    running = false;
                    const sheet = find(menu.readerMenu.contentItem, "reader-settings-sheet");
                    const capturing = sheet.grabToImage(result => {
                        result.saveToFile("/tmp/enclosure-reader-settings.png");
                        console.log("PASS: settings stay open after voice, speed, limit, fullscreen and mode changes; Done still closes");
                        Qt.quit();
                    });
                    if (!capturing) throw Error("Settings preview could not be captured");
                }
                phase++;
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
