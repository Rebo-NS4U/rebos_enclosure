import QtQuick
import Quickshell
import Quickshell.Wayland
ShellRoot {
    PanelWindow {
        id: window
        implicitWidth: 640
        implicitHeight: 600
        exclusionMode: ExclusionMode.Ignore
        TypingMenu {
            id: menu
            anchors.fill: parent
            // Stress renderer metrics beyond the estimated page-line budget.
            function readerHtml(value) {
                return '<p style="line-height:220%; margin:0px;">' + value + '</p>';
            }
        }
    }
    function find(item) {
        if (item.objectName === "reader-page-text") return item;
        for (const child of item.children) { const found = find(child); if (found) return found; }
        return null;
    }
    Timer {
        property int step: 0
        interval: 500
        running: true
        repeat: true
        onTriggered: {
            if (step === 0) {
                menu.practicing = true;
                menu.fullscreen = true; menu.readingMode = true;
                menu.pageSource = "A gentle morning with words to read and a final line that must remain visible. ".repeat(300);
            } else {
                const reader = find(menu);
                if (!menu.passage.length || reader.contentHeight > reader.height)
                    throw new Error("Reader clipped at height " + window.height + ": " + reader.contentHeight + " > " + reader.height);
                if (step === 3) { console.log("PASS: reading pages fit at three window heights"); Qt.quit(); }
                window.implicitHeight -= 100;
            }
            step++;
        }
    }
}
