import QtQuick
import Quickshell
import Quickshell.Wayland
ShellRoot {
    PanelWindow {
        id: window
        implicitWidth: 640
        implicitHeight: 800
        exclusionMode: ExclusionMode.Ignore
        TypingMenu {
            id: menu
            anchors.fill: parent

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
                menu.fullscreen = true;
                menu.paragraphStarts = Array.from({length: 299}, (_, i) => (i + 1) * 79);
                menu.pageSource = "A gentle morning with words to read and a final line that must remain visible. ".repeat(300);
            } else {
                const reader = find(menu);
                if (!menu.passage.length || reader.contentHeight > reader.height)
                    throw new Error("Reader clipped at height " + window.height + ": " + reader.contentHeight + " > " + reader.height);
                if (!/[\n\u2029]/.test(reader.getText(0, reader.length)))
                    { console.log("FAIL: Paragraph break missing", JSON.stringify(reader.getText(0, reader.length)), menu.paragraphStarts.length, menu.passage.length); Qt.quit(); return; }
                const first = reader.positionToRectangle(0);
                const next = reader.positionToRectangle(79);
                const previous = reader.positionToRectangle(77);
                if (first.x < 39 || next.x < 39 || next.y - previous.y < menu.readerLineHeight * 1.8) {
                    console.log("FAIL: paragraph indent or empty line", first.x, next.x, next.y - previous.y, menu.readerLineHeight);
                    Qt.quit(); return;
                }
                if (step === 3) { console.log("PASS: paragraph breaks render and pages fit at three window heights"); Qt.quit(); }
                window.implicitHeight -= 100;
            }
            step++;
        }
    }
}
