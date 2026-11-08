import QtQuick
import Quickshell
import QtTest
ShellRoot {
    PanelWindow {
        implicitWidth: 960; implicitHeight: 800
        Item {
            anchors.fill: parent
            TestEvent { id: keys }
            TypingMenu { id: menu; anchors.fill: parent }
        }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const found = find(child, name); if (found) return found; }
        return null;
    }
    Timer {
        interval: 500; running: true; repeat: true
        property int phase: 0
        property string prefix: "The already typed passage "
        onTriggered: {
            try {
                const input = find(menu, "typing-input");
                if (phase === 0) {
                    menu.practicing = true; menu.fullscreen = true; menu.position = 4434;
                    menu.pageSource = "The already typed passage A new sentence to continue. ".repeat(100);
                    menu.fitPage(); input.text = prefix; input.cursorPosition = input.length;
                    menu.focusPassage(); phase++; return;
                }
                if (phase === 1) {
                    if (!input.activeFocus) throw Error("Input focus missing");
                    if (!keys.keyClickChar("A", Qt.ShiftModifier, 0)) throw Error("Could not send Shift+A");
                    if (input.text !== prefix + "A") throw Error("Shift+A changed the typed prefix: " + JSON.stringify(input.text));
                    input.selectAll();
                    if (!keys.keyClickChar("A", Qt.ShiftModifier, 0)) throw Error("Could not send selected Shift+A");
                    if (input.text !== prefix + "AA") throw Error("Hidden selection lets Shift+A replace the entire passage: " + JSON.stringify(input.text));
                    keys.keyClick(Qt.Key_A, Qt.ControlModifier, 0);
                    if (input.selectedText.length) throw Error("Select All created an invisible selection");
                    keys.keyClickChar("A", Qt.ShiftModifier, 0);
                    if (input.text !== prefix + "AAA") throw Error("Ctrl+A then Shift+A lost input");
                    input.selectAll(); keys.keyClick(Qt.Key_Backspace, 0, 0);
                    if (input.text !== prefix + "AA") throw Error("Backspace deleted a hidden selection");
                    menu.turningPage = true; menu.busy = true;
                    keys.keyClickChar("A", Qt.ShiftModifier, 0);
                    if (menu.pendingKeys !== "A" || input.text !== prefix + "AA") throw Error("Shift+A was lost during a text handoff");
                    menu.turningPage = false; menu.busy = false;
                    if (menu.position !== 4434) throw Error("Typing changed the book bookmark");
                    console.log("PASS: real Shift+A key events preserve typed text, even with a stale invisible selection");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
