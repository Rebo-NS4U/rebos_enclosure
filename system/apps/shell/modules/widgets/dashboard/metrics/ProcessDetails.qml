pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.components
import qs.modules.services
import qs.modules.theme
import "ProcessTree.js" as ProcessTree

ColumnLayout {
    id: root
    objectName: "monitor-process-details"
    spacing: Styling.spacing(8)
    property int expandedPpid: -1
    readonly property string metric: SystemResources.detailMetric
    readonly property string gpuDevice: metric.startsWith("gpu:") ? metric.slice(4) : ""

    function value(row): real {
        if (gpuDevice) return row.gpu?.[gpuDevice] ?? 0;
        if (metric === "network") return row.sockets ?? 0;
        return row[metric] ?? 0;
    }
    function formatted(row): string {
        const v = value(row);
        if (metric === "cpu" || gpuDevice) return v.toFixed(1) + "%";
        if (metric === "network") return v + " sockets";
        return (v / 1024 / 1024).toFixed(1) + (metric === "disk" ? " MiB/s" : " MiB");
    }
    readonly property list<var> groups: ProcessTree.groups(SystemResources.processes, root.metric, root.gpuDevice)

    function processStats(row): string {
        return "CPU " + row.cpu.toFixed(1) + "% · RAM " + (row.ram / 1048576).toFixed(1)
            + " MiB\nDisk " + (row.io_available ? (row.disk / 1048576).toFixed(2) + " MiB/s" : "unavailable")
            + " · " + row.sockets + " sockets"
            + (root.gpuDevice ? " · GPU " + root.formatted(row) : "");
    }

    RowLayout {
        Layout.fillWidth: true
        MetricAction { text: "← All stats"; onClicked: SystemResources.detailMetric = "" }
        Item { Layout.fillWidth: true }
        StyledText { text: "Live · process trees"; font.pixelSize: Styling.fontSize(-3); color: Colors.overSurfaceVariant }
    }
    StyledText {
        Layout.fillWidth: true
        text: SystemResources.detailTitle
        font.bold: true
        wrapMode: Text.Wrap
    }
    StyledText {
        Layout.fillWidth: true
        font.pixelSize: Styling.fontSize(-3)
        color: Colors.overSurfaceVariant
        wrapMode: Text.Wrap
        text: root.metric === "network" ? "Sorted by open sockets, including local sockets. Per-process network speeds are unavailable."
            : root.metric === "disk" ? "Read + write activity across all disks; this is not space occupied on the selected disk. Restricted processes may be unavailable."
            : root.gpuDevice ? "GPU engine time reported by the driver. Processes without accessible GPU counters are omitted."
            : root.metric === "cpu" ? "CPU uses 100% per core. Expand a tree to see nested subprocesses and their individual usage."
            : "Resident memory of each tree, including shared pages. Indentation shows parent/child relationships."
    }
    ListView {
        id: list
        objectName: "monitor-process-list"
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(340, Math.max(100, contentHeight))
        clip: true
        spacing: Styling.spacing(6)
        model: ScriptModel { values: root.groups; objectProp: "ppid" }
        ScrollBar.vertical: ScrollBar { }
        delegate: StyledRect {
            id: groupRow
            required property var modelData
            width: list.width - 12
            implicitHeight: groupColumn.implicitHeight + 16
            variant: "internalbg"
            radius: Styling.radius(2)
            ColumnLayout {
                id: groupColumn
                anchors.fill: parent
                anchors.margins: 8
                spacing: Styling.spacing(6)
                Item {
                    Layout.fillWidth: true
                    implicitHeight: groupLabel.implicitHeight
                    StyledText {
                        id: groupLabel
                        width: parent.width
                        font.pixelSize: Styling.fontSize(-2)
                        wrapMode: Text.Wrap
                        text: (root.expandedPpid === groupRow.modelData.ppid ? "▾ " : "▸ ")
                            + groupRow.modelData.name + " · PID " + groupRow.modelData.ppid
                            + "\n" + groupRow.modelData.children.length + " processes in tree · " + root.formatted(groupRow.modelData)
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.expandedPpid = root.expandedPpid === groupRow.modelData.ppid ? -1 : groupRow.modelData.ppid
                    }
                }
                Repeater {
                    model: root.expandedPpid === groupRow.modelData.ppid ? groupRow.modelData.children : []
                    StyledText {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.leftMargin: Math.min(modelData.depth, 8) * 12
                        font.pixelSize: Styling.fontSize(-3)
                        wrapMode: Text.Wrap
                        text: (modelData.depth ? "↳ " : "") + modelData.name
                            + " · PID " + modelData.pid + " · PPID " + modelData.ppid
                            + "\n" + root.processStats(modelData)
                    }
                }
            }
        }
        StyledText {
            anchors.centerIn: parent
            width: parent.width - 20
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            visible: list.count === 0
            text: SystemResources.processes.length === 0 ? "Collecting processes…" : "No accessible processes for this stat."
            font.pixelSize: Styling.fontSize(-2)
        }
    }
}
