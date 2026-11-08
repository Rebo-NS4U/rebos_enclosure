import QtQuick
import Quickshell
import qs.config
ShellRoot {
    PanelWindow {
        implicitWidth: 960; implicitHeight: 700
        TypingMenu { id: menu; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const found = find(child, name); if (found) return found; }
        return null;
    }
    Timer {
        interval: 120; running: true; repeat: true
        property int step: 0
        property string retained: ""
        onTriggered: {
            try {
                const input = find(menu, "typing-input");
                if (step === 0) {
                    menu.practicing = true; menu.fullscreen = true;
                    menu.position = 124;
                    menu.pageSource = "A gentle morning with words to type. ".repeat(120);
                    menu.fitPage(); menu.focusPassage();
                } else if (step === 1) {
                    input.text = "A";
                    if (!menu.feedbackEvents || !menu.activeEffects) throw Error("Correct letter feedback missing");
                    input.text = "AZ";
                    if (!menu.failureEvents) throw Error("Error feedback missing");
                    const pulse = find(menu, "typing-character-1");
                    if (!pulse.visible || !pulse.incorrect) throw Error("Error pulse is not rendered");
                    menu.restoring = true;
                    const offset = menu.pageLayout.words.find(word => word.line >= 3).start;
                    input.text = menu.passage.slice(0, offset);
                    menu.restoring = false;
                    input.insert(input.length, menu.passage.charAt(input.length));
                    input.cursorPosition = input.length;
                    menu.refreshPageCaret();
                    retained = input.text;
                } else if (step === 2) {
                    if (!menu.lineTransitions) throw Error("Line feedback missing");
                    const shortcut = menu.modeShortcut;
                    if (!shortcut.enabled || shortcut.sequence.toString() !== "Ctrl+Tab") throw Error("Mode shortcut unavailable");
                    shortcut.activated();
                    if (!menu.readingMode || !menu.fullscreen || menu.activeEffects) throw Error("Mode shortcut failed to enter reading and clear typing effects");
                } else if (step === 3) {
                    menu.modeShortcut.activated();
                    if (menu.readingMode || !menu.fullscreen || input.text !== retained || menu.position !== 124)
                        throw Error("Mode switching lost activity size or progress");
                    menu.wordTools.open();
                    if (menu.modeShortcut.enabled) throw Error("Shortcut active in notes");
                    menu.wordTools.close();
                    Config.animDuration = 0;
                    input.insert(input.length, menu.passage.charAt(input.length));
                    if (menu.activeEffects) throw Error("Reduced motion left typing effects running");
                    console.log("PASS: fullscreen letter/error/line feedback renders; Ctrl+Tab toggles modes retaining input; notes and reduced motion are respected");
                    Qt.quit();
                }
                step++;
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
