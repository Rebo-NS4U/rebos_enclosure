import QtQuick
import Quickshell
import qs.modules.bar.layouts
import qs.modules.theme
ShellRoot {
    PanelWindow {
        implicitWidth: 760
        implicitHeight: 520
        color: "transparent"
        TypingMenu { id: practice; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (let child of item.children ?? []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        property int phase: 0
        interval: Math.max(900, Motion.base * 1.5)
        running: true
        repeat: true
        onTriggered: {
            try {
                if (phase === 0) {
                    const bar = Qt.createComponent("modules/bar/layouts/IslandBar.qml");
                    if (bar.status === Component.Error) throw Error(bar.errorString());
                    practice.loadPreset(0); practice.start();
                    if (practice.passage.length > 90 || practice.implicitHeight !== 220) throw Error("Practice is not compact");
                } else {
                    const input = find(practice, "typing-input");
                    const first = find(practice, "typing-character-0");
                    if (!input || !first) throw Error("Typing input or glyph missing");
                    if (phase === 1) {
                        if (Math.abs(first.opacity - 0.28) > 0.001) throw Error("Faint initial glyph missing");
                        input.text = practice.passage[0];
                    } else if (phase === 2) {
                        if (first.opacity !== 1) throw Error("Typed glyph did not become opaque after animation");
                        input.text = "";
                    } else {
                        if (Math.abs(first.opacity - 0.28) > 0.001) throw Error("Backspace did not restore faint glyph");
                        let count = 0;
                        while (practice.rounds < 1 && count++ < 20) input.text = practice.passage;
                        if (practice.rounds !== 1 || practice.position !== 0) throw Error("Continuous loop failed");
                        console.log("PASS: compact layout, animated glyph opacity, backspace, passage advance and continuous loop");
                        Qt.quit();
                    }
                }
                phase++;
            } catch (error) { console.error(error); Qt.quit(); }
        }
    }
}
