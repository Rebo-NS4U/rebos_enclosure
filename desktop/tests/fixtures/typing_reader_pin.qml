import QtQuick
import Quickshell
import qs.modules.bar.layouts
ShellRoot {
    PanelWindow {
        id: panel
        implicitWidth: 1280; implicitHeight: 1000
        IslandBar { id: bar; screen: panel.screen }
    }
    Timer {
        interval: 500; repeat: true; running: true
        property int phase: 0
        property var originalWindow: null
        onTriggered: {
            try {
                const reader = bar.typingPractice;
                if (phase === 0) { bar.expand("typing"); phase++; return; }
                if (phase === 1) { originalWindow = reader.Window.window; reader.pinRequested(); phase++; return; }
                if (phase === 2) {
                    if (!reader.pinned || !reader.visible || !reader.enabled || bar.currentMode !== "collapsed") throw Error("Pin did not detach reader");
                    if (reader.Window.window.title !== "rebos_shell Reader") throw Error("Reader did not move to desktop window");
                    bar.expand("typing");
                    if (bar.currentMode !== "collapsed") throw Error("Opening pinned reader also opened panel");
                    reader.pinRequested(); phase++; return;
                }
                if (!reader.visible || reader.pinned || bar.currentMode !== "typing" || reader.Window.window !== originalWindow) throw Error("Unpin did not return reader to panel: visible=" + reader.visible + " pinned=" + reader.pinned + " mode=" + bar.currentMode + " title=" + reader.Window.window.title);
                reader.backRequested();
                console.log("PASS: reader pins into desktop window, stays open and unpins to panel");
                Qt.quit();
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
