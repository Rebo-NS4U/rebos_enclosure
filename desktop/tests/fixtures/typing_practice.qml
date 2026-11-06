import QtQuick
import Quickshell
import qs.modules.bar.layouts
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
        interval: 900
        running: true
        onTriggered: {
            try {
                const bar = Qt.createComponent("modules/bar/layouts/IslandBar.qml");
                if (bar.status === Component.Error) throw Error(bar.errorString());
                practice.loadPreset(0); practice.start();
                const input = find(practice, "typing-input");
                const first = find(practice, "typing-character-0");
                if (!input || !first || first.opacity !== 0.28) throw Error("Faint initial glyph missing");
                input.text = practice.passage[0];
                if (first.opacity !== 1) throw Error("Typed glyph did not become opaque");
                input.text = "";
                if (first.opacity !== 0.28) throw Error("Backspace did not restore faint glyph");
                let count = 0;
                while (practice.rounds < 1 && count++ < 20) input.text = practice.passage;
                if (practice.rounds !== 1 || practice.position !== 0) throw Error("Continuous loop failed");
                console.log("PASS: faint glyphs, opaque typed glyphs, backspace, passage advance and continuous loop");
                Qt.quit();
            } catch (error) { console.error(error); Qt.quit(); }
        }
    }
}
