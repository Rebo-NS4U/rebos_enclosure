import QtQuick
import QtQuick.Window
import Quickshell
import "TypingPaging.js" as Pages
ShellRoot {
    property string sent: ""
    Window {
        visible: true
        width: 640; height: 600
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
                    practice.createDictionaryRequest = () => ({
                        readyState: 0, status: 200,
                        responseText: JSON.stringify([{meanings: [{partOfSpeech: "noun", definitions: [{definition: "Land beside a river."}]}]}]),
                        open: function(method, url) { sent = url; },
                        abort: function() {},
                        send: function() { this.readyState = XMLHttpRequest.DONE; this.onreadystatechange(); }
                    });
                    practice.openWord("bank", 16); return;
                }
                if (phase === 2) {
                    const action = find(practice.wordTools.contentItem, "typing-context-meaning");
                    if (!action.visible || !action.enabled) throw Error("Context action is not available independently of dictionary toggle");
                    action.clicked();
                    if (!sent.endsWith("/bank") || !practice.definitionText.includes("Land beside a river") || !find(practice.wordTools.contentItem, "typing-context-meaning-result").text.includes("river"))
                        throw Error("Context answer missing in word popup");
                    practice.wordTools.close();
                    if (practice.definitionRequest) throw Error("Close did not cancel context lookup");
                    practice.openWord("They", 0);
                    if (practice.meaningText) throw Error("Stale explanation retained for new word");
                    console.log("PASS: bounded occurrence context, direct dictionary lookup without AI, inline passage and definitions, cancellation, stale clearing"); Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
