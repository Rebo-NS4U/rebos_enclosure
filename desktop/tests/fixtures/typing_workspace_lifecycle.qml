import QtQuick
import Quickshell
import qs.config
import qs.modules.shell
import qs.modules.bar.layouts
ShellRoot {
    id: test
    property var panel: null
    property var island: null
    property var originalGlyph: null
    property int fits: 0
    property int pageRequest: 0
    PanelWindow { id: driver; implicitWidth: 640; implicitHeight: 600 }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    function findIsland(item) {
        if (item.typingPractice !== undefined) return item;
        for (const child of item.children || []) { const result = findIsland(child); if (result) return result; }
        return null;
    }
    Timer {
        interval: 350; running: true; repeat: true
        property int phase: 0
        onTriggered: {
            try {
                if (!Config.barReady) return;
                if (phase === 100) {
                    if (!island.typingPractice.fullscreen || island.typingPractice.pageFits <= fits)
                        throw Error("Fullscreen geometry change did not refit");
                    island.expand("dashboard");
                    find(panel.contentItem, "shell-outside-click-backdrop").clicked(null);
                    if (island.isExpanded && !island.retractingToHidden) throw Error("Dashboard outside dismissal broke");
                    console.log("PASS: outside clicks retain typing; five reopens reuse glyphs and layout; fullscreen refits; dashboard dismisses");
                    Qt.quit(); return;
                }
                if (phase === 0) {
                    Config.bar.style = "island";
                    const component = Qt.createComponent("modules/shell/UnifiedShellPanel.qml");
                    if (component.status !== Component.Ready) throw Error(component.errorString());
                    panel = component.createObject(test, {targetScreen: driver.screen});
                    if (!panel) throw Error("Could not create shell panel");
                } else if (phase === 1) {
                    island = findIsland(panel.contentItem);
                    if (!island) throw Error("Island layout missing");
                    island.expand("typing");
                    const typing = island.typingPractice;
                    typing.practicing = true;
                    typing.bookId = "lifecycle-fixture";
                    typing.bookLength = 1000000;
                    typing.pageSource = "A retained typing workspace with words to practice. ".repeat(100);
                    typing.fitPage();
                } else if (phase === 2) {
                    // The fixture seeded text before the opening morph laid out.
                    // Settle that initial geometry before measuring reopen reuse.
                    if (island.typingPractice.fittedGeometry !== island.typingPractice.pageGeometry()) { island.typingPractice.fitPage(); return; }
                    const backdrop = find(panel.contentItem, "shell-outside-click-backdrop");
                    backdrop.clicked(null);
                    if (island.currentMode !== "typing") throw Error("Outside click closed typing");
                    originalGlyph = island.typingPractice.glyphItems[0];
                    fits = island.typingPractice.pageFits;
                    pageRequest = island.typingPractice.pageRequest;
                    island.collapse();
                } else if (phase % 2 === 1 && phase < 13) {
                    island.expand("typing"); island.typingPractice.reopen();
                } else {
                    const typing = island.typingPractice;
                    if (typing.pageRequest !== pageRequest || typing.pageFits !== fits || typing.glyphItems[0] !== originalGlyph)
                        throw Error("Reopen reloaded or rebuilt the workspace: " + fits + " -> " + typing.pageFits);
                    if (phase === 12) {
                        typing.toggleFullscreen(); phase = 100; return;
                    }
                    island.collapse();
                }
                phase++;
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
