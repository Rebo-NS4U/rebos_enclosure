//@ pragma UseQApplication
//@ pragma ShellId enclosure-compact-resources
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Services.SystemTray
import qs.modules.components
import qs.modules.services
import qs.modules.theme

PanelWindow {
    id: panel
    screen: Quickshell.screens.find(s => s.name === Quickshell.env("ENCLOSURE_MONITOR_OUTPUT")) ?? Quickshell.screens[0]
    Component.onCompleted: SystemResources.compactMonitorActive = true
    anchors.left: true
    margins.left: 22
    implicitWidth: Math.min(374, screen.width - 32)
    implicitHeight: Math.min(590, screen.height - 72)
    exclusiveZone: 0
    color: "transparent"
    WlrLayershell.namespace: "enclosure-compact-resources"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
    readonly property var stats: SystemResources
    readonly property string mount: stats.validDisks[0] || "/"
    readonly property var matches: stats.processes.filter(p =>
        p.name.toLowerCase().includes(search.text.trim().toLowerCase()) || String(p.pid) === search.text.trim()
    ).sort((a, b) => b.cpu - a.cpu || b.ram - a.ram || a.pid - b.pid)
    property var selected: null
    property string actionMessage: ""
    property real peakRate: 1024
    readonly property real rate: Math.max(stats.networkDownloadSpeed, stats.networkUploadSpeed)
    onRateChanged: peakRate = Math.max(peakRate, rate)

    function size(bytes): string {
        const units = ["B", "K", "M", "G", "T"];
        let unit = 0;
        while (bytes >= 1024 && unit < units.length - 1) { bytes /= 1024; unit++; }
        return bytes.toFixed(bytes > 0 && bytes < 10 && unit > 0 ? 1 : 0) + units[unit];
    }
    function dismiss() { Qt.quit(); }

    IpcHandler { target: "monitor"; function close(): void { Qt.callLater(panel.dismiss); } }

    Process {
        id: terminate
        onExited: code => panel.actionMessage = code === 0 ? "Termination requested" : "Process exited or permission denied"
    }

    component Caption: StyledText {
        font.family: "monospace"
        font.pixelSize: 13
        color: Colors.overBackground
        textFormat: Text.PlainText
        elide: Text.ElideRight
    }
    component Rule: RowLayout {
        property alias title: label.text
        property string detail: ""
        id: rule
        Layout.fillWidth: true
        Caption { id: label; font.bold: true }
        Rectangle { Layout.fillWidth: true; height: 1; color: Colors.outline }
        Caption { text: rule.detail; visible: text.length > 0 }
    }
    component Gauge: ColumnLayout {
        id: gauge
        required property string title
        required property real fraction
        required property string reading
        Layout.fillWidth: true
        Layout.preferredWidth: 1
        spacing: 1
        Caption { text: gauge.title; Layout.alignment: Qt.AlignHCenter }
        Canvas {
            id: dial
            Layout.alignment: Qt.AlignHCenter
            implicitWidth: 62
            implicitHeight: 48
            property real fraction: gauge.fraction
            property color ink: Colors.overBackground
            property color track: Colors.outline
            onFractionChanged: requestPaint()
            onInkChanged: requestPaint()
            onTrackChanged: requestPaint()
            onPaint: {
                const c = getContext("2d");
                c.clearRect(0, 0, width, height);
                c.save();
                c.translate(width / 2, 32);
                const start = 0.82 * Math.PI, sweep = 1.36 * Math.PI;
                const angle = start + sweep * Math.min(1, Math.max(0, fraction));
                c.strokeStyle = track;
                c.lineWidth = 1;
                c.beginPath(); c.arc(0, 0, 23, start, start + sweep); c.stroke();
                for (let i = 0; i <= 8; i++) {
                    const a = start + sweep * i / 8;
                    c.beginPath();
                    c.moveTo(19 * Math.cos(a), 19 * Math.sin(a));
                    c.lineTo(23 * Math.cos(a), 23 * Math.sin(a)); c.stroke();
                }
                c.strokeStyle = ink; c.fillStyle = ink; c.lineWidth = 2;
                c.beginPath(); c.arc(0, 0, 23, start, angle); c.stroke();
                c.beginPath(); c.moveTo(0, 0); c.lineTo(17 * Math.cos(angle), 17 * Math.sin(angle)); c.stroke();
                c.beginPath(); c.arc(0, 0, 2.5, 0, Math.PI * 2); c.fill();
                c.restore();
            }
        }
        Caption { text: gauge.reading; Layout.alignment: Qt.AlignHCenter }
    }
    component Meter: RowLayout {
        id: meter
        required property string title
        required property real fraction
        required property string reading
        Layout.fillWidth: true
        Caption { text: meter.title; Layout.preferredWidth: 30 }
        StandardProgressBar { Layout.fillWidth: true; value: meter.fraction; showCursor: false }
        Caption { text: meter.reading; Layout.preferredWidth: 90; horizontalAlignment: Text.AlignRight }
    }

    Rectangle {
        anchors.fill: parent
        color: Colors.background
        radius: Styling.radius(0)
        border.color: Colors.outline
        Shortcut { sequence: "Escape"; onActivated: panel.dismiss() }
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 15
            spacing: 7
            RowLayout {
                Rule { title: "system" }
                ThemeButton { text: "×"; Accessible.name: "Close monitor"; onClicked: panel.dismiss() }
            }
            RowLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                Gauge { title: "cpu"; fraction: panel.stats.cpuUsage / 100; reading: Math.round(panel.stats.cpuUsage) + "%" }
                Gauge { title: "mem"; fraction: panel.stats.ramUsage / 100; reading: panel.size(panel.stats.ramUsed * 1024) }
                Gauge { title: "swp"; fraction: panel.stats.swapUsed / (panel.stats.swapTotal || 1); reading: panel.size(panel.stats.swapUsed * 1024) }
                Gauge { title: "tmp"; fraction: panel.stats.cpuTemp / 100; reading: panel.stats.cpuTemp < 0 ? "—" : panel.stats.cpuTemp + "°" }
            }
            Meter {
                title: "dsk"; fraction: (panel.stats.diskUsage[panel.mount] || 0) / 100
                reading: panel.size(panel.stats.diskUsed[panel.mount] || 0) + "/" + panel.size(panel.stats.diskTotal[panel.mount] || 0)
            }
            Meter { title: "↓"; fraction: panel.stats.networkDownloadSpeed / panel.peakRate; reading: panel.size(panel.stats.networkDownloadSpeed) + "/s" }
            Meter { title: "↑"; fraction: panel.stats.networkUploadSpeed / panel.peakRate; reading: panel.size(panel.stats.networkUploadSpeed) + "/s" }
            Rule { title: "procs"; detail: String(panel.matches.length) }
            SearchInput {
                id: search
                Layout.fillWidth: true
                implicitHeight: 36
                placeholderText: "Filter by name or PID"
                onEscapePressed: panel.dismiss()
            }
            RowLayout {
                visible: panel.selected !== null
                Caption { Layout.fillWidth: true; text: panel.selected ? panel.selected.name + " · " + panel.selected.pid : "" }
                ThemeButton {
                    text: "End"; danger: true
                    onClicked: {
                        terminate.command = ["python3", Quickshell.shellDir + "/scripts/process_monitor.py", "--terminate",
                            String(panel.selected.pid), String(panel.selected.start)];
                        terminate.running = true;
                        panel.selected = null;
                    }
                }
                ThemeButton { text: "Cancel"; onClicked: panel.selected = null }
            }
            Caption { visible: text !== ""; text: panel.actionMessage }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: panel.matches
                ScrollBar.vertical: ScrollBar {}
                Caption { anchors.centerIn: parent; visible: parent.count === 0; text: search.text ? "No matching processes" : "Collecting processes…" }
                delegate: RowLayout {
                    required property var modelData
                    width: ListView.view.width - 10
                    height: 32
                    Caption { Layout.fillWidth: true; text: parent.modelData.name }
                    Caption { text: parent.modelData.cpu.toFixed(1) + "%" }
                    Caption { Layout.preferredWidth: 44; horizontalAlignment: Text.AlignRight; text: panel.size(parent.modelData.ram) }
                    ThemeButton {
                        text: "end"; padding: 3; implicitHeight: 26
                        enabled: parent.modelData.pid > 1 && !terminate.running
                        onClicked: { panel.selected = parent.modelData; panel.actionMessage = ""; }
                    }
                }
            }
            Rule { title: "background"; detail: String(tray.count) }
            ListView {
                id: tray
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(3, count) * 32
                clip: true
                model: SystemTray.items
                ScrollBar.vertical: ScrollBar {}
                delegate: ItemDelegate {
                    id: app
                    required property var modelData
                    width: ListView.view.width
                    height: 32
                    contentItem: RowLayout {
                        Image { source: app.modelData.icon; Layout.preferredWidth: 18; Layout.preferredHeight: 18; fillMode: Image.PreserveAspectFit }
                        Caption { Layout.fillWidth: true; text: app.modelData.title || app.modelData.id }
                        Caption { text: "›" }
                    }
                    onClicked: {
                        if (modelData.onlyMenu && modelData.hasMenu) modelData.display(panel, x + width, mapToItem(panel.contentItem, 0, 0).y);
                        else modelData.activate();
                    }
                }
            }
        }
    }
}
