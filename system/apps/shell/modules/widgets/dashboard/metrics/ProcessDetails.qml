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
    readonly property real listedRam: SystemResources.processes.reduce((total, row) => total + (row.ram || 0), 0)

    function memorySize(bytes): string {
        return (bytes / 1024 / 1024).toFixed(1) + " MiB";
    }

    RowLayout {
        Layout.fillWidth: true
        MetricAction { text: "← All stats"; onClicked: SystemResources.detailMetric = "" }
        Item { Layout.fillWidth: true }
        StyledText { text: "Live · process trees"; font.pixelSize: Styling.fontSize(-3); color: Colors.overSurfaceVariant }
    }
    StyledText {
        Layout.fillWidth: true
        visible: root.metric === "ram"
        wrapMode: Text.Wrap
        font.pixelSize: Styling.fontSize(-3)
        text: "System RAM: " + root.memorySize(SystemResources.ramUsed * 1024) + " used + "
            + root.memorySize(SystemResources.ramAvailable * 1024) + " available = "
            + root.memorySize(SystemResources.ramTotal * 1024) + " total"
            + "\nListed process memory (RSS): " + root.memorySize(root.listedRam)
            + " across " + SystemResources.processes.length + " processes"
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
            : "All readable processes are grouped into trees; expand a tree to see its entries. Process memory (RSS) counts shared pages in each process, so adding rows can count the same memory more than once. System used RAM also includes kernel memory and excludes reclaimable memory estimated as available. These totals do not add up to the same measure; restricted processes may be missing. Samples update independently."
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
                        elide: Text.ElideMiddle
                        maximumLineCount: 1
                        text: (modelData.depth ? "↳ " : "") + modelData.name
                            + " · PID " + modelData.pid + " · " + root.formatted(modelData)
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
