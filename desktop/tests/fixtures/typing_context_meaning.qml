import QtQuick
import Quickshell
import "TypingPaging.js" as Pages
ShellRoot {
    property string sent: ""
    PanelWindow {
        implicitWidth: 640; implicitHeight: 600
        TypingMenu { id: practice; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        interval: 500; running: true; repeat: true
        property int phase: 0
        onTriggered: {
            try {
                if (phase++ === 0) {
                    const text = "The bank approved a loan. " + "Other words. ".repeat(60) + "They sat on the bank of the river.";
                    const snippet = Pages.wordContext(text, "bank", text.lastIndexOf("bank"));
                    if (snippet.indexOf("river") < 0 || snippet.indexOf("loan") >= 0 || snippet.length > 1000)
                        throw Error("Wrong occurrence or excessive context");
                    if (Pages.wordContext("A riverbank.", "bank", 0) !== "") throw Error("Matched a word fragment");
                    practice.practicing = true; practice.bookId = "meaning-fixture";
                    practice.pageSource = "They sat on the bank of the river. ".repeat(40); practice.fitPage();
                    practice.runMeaningLookup = () => {
                        sent = practice.meaningContext;
                        practice.meaningText = "Here, bank means the land beside a river.";
                        practice.meaningBusy = false;
                    };
                    practice.openWord("bank", 16); return;
                }
                if (phase === 2) {
                    const action = find(practice.wordTools.contentItem, "typing-context-meaning");
                    if (!action.visible || !action.enabled) throw Error("Context action is not available independently of dictionary toggle");
                    action.clicked();
                    if (!sent.includes("river") || !find(practice.wordTools.contentItem, "typing-context-meaning-result").text.includes("river"))
                        throw Error("Context answer missing in word popup");
                    practice.wordTools.close();
                    if (practice.meaningToken || practice.meaningBusy) throw Error("Close did not cancel context lookup");
                    practice.openWord("They", 0);
                    if (practice.meaningText || practice.meaningError) throw Error("Stale explanation retained for new word");
                    console.log("PASS: bounded occurrence context, explicit lookup, inline result, close cancellation, stale-answer clearing"); Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
