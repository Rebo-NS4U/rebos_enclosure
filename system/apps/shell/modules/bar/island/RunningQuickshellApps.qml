pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Quickshell.Io
import qs.modules.components
import qs.modules.theme
import qs.config

StyledRect {
    id: root
    property var instances: []
    property string status: "Loading…"
    property string output: ""
    implicitHeight: content.implicitHeight + Styling.spacing(24)
    variant: "internalbg"
    radius: Styling.radius(2)

    function refresh() {
        if (!query.running) query.running = true;
    }
    function appName(app) {
        const names = {
            "rebos_shell": "Enclosure Shell",
            "enclosure-music": "Music",
            "rebos_streamer": "Anime Streamer",
            "rebos-assistant-ui": "Dweebo Assistant"
        };
        const path = app.config_path || "";
        const file = path.split("/").pop() || "Quickshell";
        return names[app.shell_id] || app.shell_id || (file === "shell.qml" ? path.split("/").slice(-2, -1)[0] : file.replace(/\.qml$/, ""));
    }
    Component.onCompleted: refresh()
    Timer {
        interval: 3000
        running: root.visible
        repeat: true
        onTriggered: root.refresh()
    }
    Process {
        id: query
        command: ["qs", "list", "--all", "--json"]
        stdout: StdioCollector { onStreamFinished: root.output = text }
        onExited: (exitCode, exitStatus) => {
            try {
                if (exitCode !== 0) throw new Error("query failed");
                const apps = JSON.parse(root.output);
                if (!Array.isArray(apps)) throw new Error("invalid response");
                root.instances = apps.sort((a, b) => root.appName(a).localeCompare(root.appName(b)) || a.pid - b.pid);
                root.status = apps.length ? "" : "No running Quickshell apps on this display.";
            } catch (e) {
                root.instances = [];
                root.status = "Could not read running Quickshell apps.";
            }
        }
    }
    ColumnLayout {
        id: content
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: Styling.spacing(12) }
        spacing: Styling.spacing(8)
        StyledText {
            Layout.fillWidth: true
            text: "Running Quickshell apps (" + root.instances.length + ")"
            font.bold: true
            font.pixelSize: Styling.fontSize(-1)
        }
        StyledText {
            Layout.fillWidth: true
            visible: root.status !== ""
            text: root.status
            wrapMode: Text.Wrap
            color: Colors.overSurfaceVariant
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(appList.implicitHeight, Styling.spacing(240))
            visible: root.instances.length > 0
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                id: appList
                width: parent.width
                spacing: Styling.spacing(10)
                Repeater {
                    model: root.instances
                    ColumnLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: Styling.spacing(2)
                        StyledText {
                            Layout.fillWidth: true
                            text: root.appName(parent.modelData) + " · PID " + parent.modelData.pid
                            font.pixelSize: Styling.fontSize(-2)
                            wrapMode: Text.Wrap
                        }
                        StyledText {
                            Layout.fillWidth: true
                            text: parent.modelData.config_path || "Unknown config"
                            font.pixelSize: Styling.fontSize(-3)
                            color: Colors.overSurfaceVariant
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }
            }
        }
    }
}
