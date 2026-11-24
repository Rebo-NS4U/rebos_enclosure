pragma ComponentBehavior: Bound
import QtQuick
import qs.config
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Services.SystemTray
import qs.modules.components
import qs.modules.services
import qs.modules.widgets.dashboard.metrics
import qs.modules.theme

Item {
    id: panel
    objectName: "compact-resource-monitor"
    signal closeRequested()
    signal backRequested()
    readonly property var stats: SystemResources
    readonly property string mount: stats.validDisks[0] || "/"
    property string sortMetric: "cpu"
    property bool descending: true
    readonly property bool showingSensors: sortMetric === "temp"
    readonly property var matches: {
        const metric = sortMetric;
        const direction = descending ? -1 : 1;
        const query = search.text.trim().toLowerCase();
        const rows = showingSensors ? stats.temperatures : stats.processes;
        return rows.filter(row => row.name.toLowerCase().includes(query)
            || (!showingSensors && String(row.pid) === query)).sort((a, b) => {
            const x = a[metric], y = b[metric];
            if ((x == null) !== (y == null)) return x == null ? 1 : -1;
            const difference = direction * (x - y);
            if (difference) return difference;
            if (showingSensors) return a.id.localeCompare(b.id);
            if (metric === "cpu" && a.ram !== b.ram) return b.ram - a.ram;
            return a.pid - b.pid;
        });
    }

    onMatchesChanged: {
        // Update rows in place so sampling can reorder results without resetting scroll.
        const sharedCount = Math.min(resultRows.count, matches.length);
        for (let index = 0; index < sharedCount; ++index)
            resultRows.setProperty(index, "entry", matches[index]);
        if (resultRows.count > matches.length)
            resultRows.remove(matches.length, resultRows.count - matches.length);
        for (let index = sharedCount; index < matches.length; ++index)
            resultRows.append({entry: matches[index]});
    }

    ListModel {
        id: resultRows
        dynamicRoles: true
    }

    function sortBy(metric: string) {
        descending = sortMetric === metric ? !descending : true;
        sortMetric = metric;
        selected = null;
        actionMessage = "";
        results.positionViewAtBeginning();
    }
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
    Process {
        id: terminate
        onExited: code => panel.actionMessage = code === 0 ? "Termination requested" : "Process exited or permission denied"
    }

    component Caption: StyledText {
        font.pixelSize: Styling.fontSize(-1)
        color: Styling.srItem("bg")
        textFormat: Text.PlainText
        elide: Text.ElideRight
    }
    component Rule: RowLayout {
        property alias title: label.text
        property string detail: ""
        id: rule
        Layout.fillWidth: true
        Caption { id: label; font.weight: Font.DemiBold; color: Colors.primary }
        Rectangle { Layout.fillWidth: true; height: 1; color: Qt.alpha(Styling.srItem("bg"), 0.24) }
        Caption { text: rule.detail; visible: text.length > 0 }
    }
    component SortButton: ToolButton {
        id: button
        required property string metric
        required property string title
        Layout.fillWidth: true
        readonly property bool activeSort: panel.sortMetric === metric
        objectName: "sort-" + metric
        focusPolicy: Qt.StrongFocus
        hoverEnabled: true
        padding: Styling.spacing(8)
        Accessible.name: "Sort by " + title + (activeSort ? (panel.descending ? ", descending" : ", ascending") : "")
        onClicked: panel.sortBy(metric)
        contentItem: Caption { text: button.heading }
        background: StyledRect {
            buttonSurface: true
            controlPressed: button.down
            variant: button.hovered || button.visualFocus ? "focus" : "internalbg"
            radius: Styling.radius(-4)
            border.width: button.visualFocus ? Config.controlBorderWidth : 0
            border.color: Colors.primary
        }
        readonly property string heading: title + (activeSort ? (panel.descending ? " ↓" : " ↑") : "")
    }
    component Gauge: SortButton {
        id: gauge
        required property real fraction
        required property string reading
        Layout.preferredWidth: 1
        contentItem: ColumnLayout {
            spacing: Styling.spacing(5)
            Caption {
                Layout.fillWidth: true
                text: gauge.heading
                color: gauge.activeSort ? Colors.primary : Styling.srItem("internalbg")
            }
            Caption {
                Layout.fillWidth: true
                text: gauge.reading
                color: Styling.srItem("internalbg")
                font.weight: Font.DemiBold
                font.pixelSize: Styling.fontSize(0)
            }
            StandardProgressBar {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
                value: gauge.fraction
                showCursor: false
            }
        }
    }
    component Meter: RowLayout {
        id: meter
        required property string title
        required property real fraction
        required property string reading
        Layout.fillWidth: true
        Caption { text: meter.title; Layout.preferredWidth: Math.max(Styling.spacing(72), implicitWidth) }
        StandardProgressBar { Layout.fillWidth: true; value: meter.fraction; showCursor: false }
        Caption { text: meter.reading; Layout.preferredWidth: 90; horizontalAlignment: Text.AlignRight }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Styling.spacing(16)
        spacing: Styling.spacing(7)
        RowLayout {
            IslandBackButton { onClicked: panel.backRequested() }
            StyledText {
                Layout.fillWidth: true
                text: "System Monitor"
                font.pixelSize: Styling.fontSize(3)
                font.bold: true
                color: Colors.overBackground
            }
            ThemeButton { text: "×"; Accessible.name: "Close monitor"; onClicked: panel.closeRequested() }
        }
        Separator { Layout.fillWidth: true; implicitHeight: 1 }
        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(6)
            Gauge { metric: "cpu"; title: "CPU"; fraction: panel.stats.cpuUsage / 100; reading: Math.round(panel.stats.cpuUsage) + "%" }
            Gauge { metric: "ram"; title: "Memory"; fraction: panel.stats.ramUsage / 100; reading: panel.size(panel.stats.ramUsed * 1024) }
            Gauge {
                metric: "disk"; title: "Disk"
                fraction: (panel.stats.diskUsage[panel.mount] || 0) / 100
                reading: panel.size(panel.stats.diskUsed[panel.mount] || 0) + "/" + panel.size(panel.stats.diskTotal[panel.mount] || 0)
            }
            Gauge { metric: "temp"; title: "Temp"; fraction: panel.stats.cpuTemp / 100; reading: panel.stats.cpuTemp < 0 ? "—" : panel.stats.cpuTemp + "°" }
        }
        SortButton {
            id: swapBar
            metric: "swap"; title: "Swap"
            padding: Styling.spacing(5)
            contentItem: Meter {
                title: swapBar.heading
                fraction: panel.stats.swapTotal > 0 ? panel.stats.swapUsed / panel.stats.swapTotal : 0
                reading: panel.size(panel.stats.swapUsed * 1024) + "/" + panel.size(panel.stats.swapTotal * 1024)
            }
        }
        Meter { title: "Download"; fraction: panel.stats.networkDownloadSpeed / panel.peakRate; reading: panel.size(panel.stats.networkDownloadSpeed) + "/s" }
        Meter { title: "Upload"; fraction: panel.stats.networkUploadSpeed / panel.peakRate; reading: panel.size(panel.stats.networkUploadSpeed) + "/s" }
        Rule { title: panel.showingSensors ? "Temperature sensors" : "Processes"; detail: String(panel.matches.length) }
        SearchInput {
            id: search
            objectName: "resource-filter"
            Layout.fillWidth: true
            implicitHeight: 36
            placeholderText: panel.showingSensors ? "Filter sensors by name" : "Filter by name or PID"
            onTextChanged: results?.positionViewAtBeginning()
            onEscapePressed: panel.backRequested()
        }
        RowLayout {
            visible: panel.selected !== null
            Caption { Layout.fillWidth: true; text: panel.selected ? panel.selected.name + " · " + panel.selected.pid : "" }
            MetricAction {
                text: "End process"
                danger: true
                emphasized: true
                onClicked: {
                    terminate.command = ["python3", Quickshell.shellDir + "/scripts/process_monitor.py", "--terminate",
                        String(panel.selected.pid), String(panel.selected.start)];
                    terminate.running = true;
                    panel.selected = null;
                }
            }
            MetricAction { text: "Cancel"; onClicked: panel.selected = null }
        }
        Caption { visible: text !== ""; text: panel.actionMessage }
        ListView {
            id: results
            objectName: "resource-results"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: resultRows
            ScrollBar.vertical: ScrollBar {}
            Caption { anchors.centerIn: parent; visible: results.count === 0; text: panel.showingSensors ? (search.text ? "No matching sensors" : "No temperature sensors available")
                : search.text ? "No matching processes" : "Collecting processes…" }
            delegate: RowLayout {
                id: row
                required property var entry
                readonly property bool isSensor: entry.temp !== undefined
                width: ListView.view.width - 10
                height: Math.max(Styling.spacing(32), implicitHeight + Styling.spacing(4))
                Caption { Layout.fillWidth: true; text: row.entry.name }
                Caption {
                    text: row.isSensor ? row.entry.temp.toFixed(1) + " °C"
                        : row.entry.cpu.toFixed(1) + "%"
                }
                Caption {
                    visible: !row.isSensor
                    Layout.preferredWidth: panel.sortMetric === "disk" ? 68 : 44
                    horizontalAlignment: Text.AlignRight
                    text: {
                        if (row.isSensor) return "";
                        if (panel.sortMetric === "disk")
                            return row.entry.disk == null ? "—" : panel.size(row.entry.disk) + "/s";
                        if (panel.sortMetric === "swap")
                            return row.entry.swap == null ? "—" : panel.size(row.entry.swap);
                        return panel.size(row.entry.ram);
                    }
                }
                MetricAction {
                    text: "End"
                    danger: true
                    Accessible.name: "End " + row.entry.name
                    visible: !row.isSensor
                    enabled: !row.isSensor && row.entry.pid > 1 && !terminate.running
                    onClicked: { panel.selected = row.entry; panel.actionMessage = ""; }
                }
            }
        }
        Rule { title: "Background"; detail: String(tray.count) }
        ListView {
            id: tray
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(3, count) * 32
            clip: true
            model: SystemTray.items
            ScrollBar.vertical: ScrollBar {}
            delegate: ItemDelegate {
                background: StyledRect { variant: app.hovered || app.visualFocus ? "focus" : "transparent" }
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
                    if (modelData.onlyMenu && modelData.hasMenu) {
                        const position = app.mapToItem(panel.QsWindow.contentItem, app.width, 0);
                        modelData.display(panel.QsWindow.window, position.x, position.y);
                    } else modelData.activate();
                }
            }
        }
    }
}
