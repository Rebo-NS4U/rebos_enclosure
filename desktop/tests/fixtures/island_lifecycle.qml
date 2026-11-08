import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.modules.bar.layouts
import qs.modules.theme

ShellRoot {
    PanelWindow {
        id: window
        implicitWidth: 1000
        implicitHeight: 900
        color: "transparent"
        mask: Region {}
        exclusionMode: ExclusionMode.Ignore
        IslandBar { id: island; screen: window.screen }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children ?? []) {
            const result = find(child, name);
            if (result) return result;
        }
        return null;
    }
    readonly property var panels: [
        ["dashboard", "dashboardView"], ["power", "powerView"],
        ["sound", "soundView"], ["mic", "micView"], ["wifi", "wifiView"],
        ["bluetooth", "bluetoothView"], ["stats", "statsView"],
        ["alerts", "alertsView"], ["wallpapers", "wallpapersView"],
        ["battery", "batteryView"], ["weather", "weatherView"],
        ["media", "mediaCenterView"], ["calendar", "calendarView"]
    ]
    Timer {
        property int step: -1
        interval: Math.max(800, Motion.base * 3)
        running: true
        repeat: true
        onTriggered: {
            try {
                const selected = step >= 0 && step % 2 === 0 ? panels[Math.floor(step / 2)][0] : "collapsed";
                for (const panel of panels) {
                    const loader = find(island, "island-panel-" + panel[1]);
                    if (!loader) throw Error("Missing loader: " + panel[0]);
                    if ((loader.item !== null) !== (panel[0] === selected)) throw Error("Unexpected panel lifetime: " + panel[0] + " while " + selected);
                    if (loader.item && loader.implicitHeight <= 0) throw Error("Panel lost its height: " + panel[0]);
                }
                if (selected === "power") {
                    const power = find(island, "island-panel-powerView").item;
                    power.moveSelection(1);
                    if (power.selectedIndex !== 0) throw Error("Power navigation failed");
                }
                step++;
                if (step >= panels.length * 2) {
                    console.log("PASS: Island panels load on demand and release after closing");
                    Qt.quit();
                } else {
                    island.currentMode = step % 2 === 0 ? panels[Math.floor(step / 2)][0] : "collapsed";
                }
            } catch (error) { console.error("ERROR: " + error); Qt.quit(); }
        }
    }
}
