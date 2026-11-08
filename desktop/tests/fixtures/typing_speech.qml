import QtQuick
import Quickshell
ShellRoot {
    PanelWindow {
        implicitWidth: 720
        implicitHeight: 650
        TypingMenu { id: menu; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        interval: 700; running: true; repeat: true
        property int step: 0
        onTriggered: {
            if (step === 0) {
                menu.practicing = true;
                menu.readingMode = true;
                menu.pageSource = "A gentle morning with many words to read. ".repeat(100);
                menu.fitPage();
            } else if (step === 1) {
                if (Quickshell.env("ENCLOSURE_READER_SPEECH_DIR") && !menu.naturalVoiceReady) throw Error("Natural voice was not detected");
                menu.toggleSpeech();
            } else if (step === 2) {
                if (!menu.speaking || menu.speechText !== menu.passage.trim()) throw Error("Page speech did not start");
                if (find(menu, "reader-speech").text !== "Stop") throw Error("Stop control missing");
                menu.toggleSpeech();
            } else if (step === 3) {
                if (menu.speaking || menu.errorMessage) throw Error("Stop failed: " + menu.errorMessage);
                find(menu, "reader-page-text").select(0, 15);
                menu.toggleSpeech();
            } else if (step === 4) {
                if (!menu.speaking || menu.speechText !== menu.passage.slice(0, 15)) throw Error("Selection not spoken");
                menu.readingMode = false;
            } else if (step === 5) {
                if (menu.speaking) throw Error("Mode switch did not stop speech");
                menu.readingMode = true;
                menu.toggleSpeech();
            } else if (step === 6) {
                menu.pageSource = "Changed page with different words. ".repeat(100);
                menu.fitPage();
            } else if (step === 7) {
                if (menu.speaking) throw Error("Page change did not stop speech");
                menu.toggleSpeech();
            } else if (step === 8) {
                menu.visible = false;
            } else {
                if (menu.speaking || menu.errorMessage) throw Error("Reader hide did not stop speech: " + menu.errorMessage);
                console.log("PASS: page and selection speech, stop control, mode/page/hide cancellation");
                Qt.quit();
            }
            step++;
        }
    }
}
