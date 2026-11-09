import QtQuick
import Quickshell
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
                    practice.wordTools.grabFocus = false; // QtTest has no native Wayland input serial.
                    practice.practicing = true; practice.bookId = "dictionary-fixture";
                    practice.createDictionaryRequest = () => ({
                        readyState: 0, status: 200,
                        responseText: JSON.stringify([{meanings: [{partOfSpeech: "noun", definitions: [{definition: "Land beside a river."}]}]}]),
                        open: function(method, url) { sent = url; },
                        abort: function() {},
                        send: function() { this.readyState = XMLHttpRequest.DONE; this.onreadystatechange(); }
                    });
                    practice.openWord("bank"); return;
                }
                if (find(practice.wordTools.contentItem, "typing-context-meaning") || find(practice.wordTools.contentItem, "typing-context-meaning-result")) throw Error("Context UI still present");
                practice.lookupDefinition(true);
                if (!sent.endsWith("/bank") || !practice.definitionText.includes("Land beside a river")) throw Error("Dictionary lookup broken");
                practice.wordTools.close();
                if (practice.definitionRequest) throw Error("Close did not cancel dictionary lookup");
                console.log("PASS: context removed; dictionary lookup remains available independently of notes");
                Qt.quit();
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
