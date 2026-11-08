import QtQuick
import Quickshell
import qs.config
ShellRoot {
    PanelWindow {
        implicitWidth: 640
        implicitHeight: 600
        TypingMenu { id: menu; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children) { const found = find(child, name); if (found) return found; }
        return null;
    }
    Timer {
        property int step: 0
        property string retainedInput: "A gentle morning"
        property int retainedPosition: 123
        interval: 500; running: true; repeat: true
        onTriggered: {
            if (step === 0) {
                menu.practicing = true;
                menu.position = retainedPosition;
                find(menu, "typing-input").text = retainedInput;
                menu.pageSource = "A gentle morning with many words to read. ".repeat(100);
            } else if (step <= 4) {
                const reading = step > 2;
                const large = step % 2 === 0;
                menu.readingMode = reading;
                menu.fullscreen = large;
                menu.fitPage();
                menu.focusPassage();
                if (find(menu, "typing-input").visible === reading) throw Error("Wrong typing visibility");
                const reader = find(menu, "reader-page-text");
                if (reader.visible !== reading) throw Error("Wrong reading visibility");
                const expectedSize = Config.theme.fontSize + 2;
                if (menu.readingFont.family !== Config.theme.font) throw Error("Passage lost shell font family");
                if (menu.readingFont.pixelSize !== expectedSize) throw Error("Wrong passage font size");
                if (find(menu, "typing-input").text !== retainedInput || menu.position !== retainedPosition)
                    throw Error("Size or activity change lost typing progress");
                if (!menu.passage.length) throw Error("Empty passage");
                if (reading && reader.contentHeight > reader.height) throw Error("Reader clipped");
                if (large) { menu.handleEscape(); if (menu.fullscreen || menu.readingMode !== reading) throw Error("Escape changed activity"); }
            } else { console.log("PASS: fullscreen typing shares reader typography; both sizes retain input and position; Escape preserves activity"); Qt.quit(); }
            step++;
        }
    }
}
