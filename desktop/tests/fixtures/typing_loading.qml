import QtQuick
import Quickshell
import Quickshell.Wayland
ShellRoot {
    PanelWindow {
        implicitWidth: 640
        implicitHeight: 600
        mask: Region {}
        TypingMenu { id: practice; anchors.fill: parent; visible: true }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children ?? []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    property int phase: 0
    property double started: 0
    Timer {
        interval: 500; running: true; repeat: true
        onTriggered: {
            try {
                if (practice.busy) return;
                const input = find(practice, "typing-input");
                if (phase === 0) {
                    practice.practicing = true;
                    practice.pageSource = "A long passage with emoji 😀 and many words. ".repeat(90);
                    started = Date.now();
                    practice.fitPage();
                    phase++; return;
                }
                practice.refreshPageCaret();
                const count = Object.keys(practice.glyphItems).length;
                if (practice.pageLayout.lines > practice.layoutLineLimit) throw Error("Page exceeds viewport line budget");
                if (practice.passage.length >= practice.pageSource.length) throw Error("Entire long section was laid out");
                if (count > practice.passage.length) throw Error("Glyph count exceeds bounded page");
                const viewport = find(practice, "typing-page-visuals");
                if (practice.implicitHeight >= 600 || practice.implicitHeight <= viewport.height) throw Error("Typing panel did not shrink around its seven rows and controls");
                if (Math.abs(viewport.height - 7 * practice.passageLineHeight) > 1) throw Error("Typing viewport must show exactly seven rows total");
                if (Math.abs(viewport.centerPadding - 3 * practice.passageLineHeight) > 1) throw Error("Blank centering rows must fit inside the seven-row viewport");
                const glyph = practice.glyphItems[practice.visualCursor];
                if (!glyph) throw Error("Cursor glyph missing after jump");
                const point = glyph.mapToItem(viewport.contentItem, 0, 0);
                if (Math.abs(point.y + practice.passageLineHeight / 2 - viewport.contentY - viewport.height / 2) > 1) throw Error("Cursor not centered");
                if (phase === 1) {
                    console.log("Long passage ready: " + count + " live glyphs / " + practice.passage.length + " characters; " + (Date.now() - started) + " ms including timer wait");
                    input.text = practice.passage.slice(0, -1); input.cursorPosition = input.length;
                    phase++; return;
                }
                if (phase === 2) {
                    input.text = ""; input.cursorPosition = 0;
                    phase++; return;
                }
                console.log("PASS: bounded long-passage glyph creation, distant cursor jumps, backtracking, Unicode and centered tracking");
                Qt.quit();
            } catch (error) { console.error(error.stack || error); Qt.quit(); }
        }
    }
}
