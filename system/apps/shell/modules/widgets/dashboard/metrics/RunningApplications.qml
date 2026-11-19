pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.modules.components
import qs.modules.theme
import qs.modules.services
import qs.config

StyledRect {
    id: root
    property var instances: []
    readonly property var applications: applicationRows(NiriService.rawWindows, instances)
    property string status: "Loading…"
    property string output: ""
    property string closingId: ""
    property string actionMessage: ""

    function applicationRows(windows, shellInstances) {
        const shellPids = new Set(shellInstances.map(app => app.pid));
        const rows = shellInstances.map(app => ({
            name: appName(app),
            detail: "Quickshell · PID " + app.pid + " · " + (app.config_path || "Unknown config"),
            instance: app
        }));
        const windowApps = new Map();
        for (const window of windows) {
            if (shellPids.has(window.pid)) continue;
            const key = window.app_id || window.id;
            const existing = windowApps.get(key);
            if (existing) {
                existing.count++;
                if (window.is_focused) existing.window = window;
            } else {
                windowApps.set(key, { window: window, count: 1 });
            }
        }
        for (const {window, count} of windowApps.values()) {
            rows.push({
                name: DesktopEntries.byId(window.app_id || "")?.name
                    || window.app_id || window.title || "Unknown application",
                detail: count > 1 ? count + " windows" : (window.title || "1 window"),
                windowId: window.id
            });
        }
        return rows.sort((a, b) => a.name.localeCompare(b.name));
    }

    function closeApp(app) {
        if (closer.running || !app.id) return;
        closingId = app.id;
        actionMessage = "";
        // Target the registry instance, avoiding stale or reused process IDs.
        closer.command = ["qs", "kill", "--id", app.id];
        closer.running = true;
    }
    Process {
        id: closer
        onExited: (exitCode, exitStatus) => {
            root.actionMessage = exitCode === 0 ? "Close requested." : "Could not close this app. It may have already exited.";
            root.closingId = "";
            root.refresh();
        }
    }
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
    onVisibleChanged: { if (visible) refresh(); }
    Component.onCompleted: { if (visible) refresh(); }
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
                root.instances = apps;
                root.status = "";
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
            text: "Applications (" + root.applications.length + ")"
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
        StyledText {
            Layout.fillWidth: true
            visible: root.actionMessage !== ""
            text: root.actionMessage
            wrapMode: Text.Wrap
            color: Colors.overSurfaceVariant
        }
        StyledText {
            Layout.fillWidth: true
            visible: root.status === "" && root.applications.length === 0
            text: "No running applications."
            color: Colors.overSurfaceVariant
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(appList.implicitHeight, Styling.spacing(160))
            visible: root.applications.length > 0
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                id: appList
                width: content.width
                spacing: Styling.spacing(10)
                Repeater {
                    model: root.applications
                    ColumnLayout {
                        id: appRow
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: Styling.spacing(2)
                        RowLayout {
                            Layout.fillWidth: true
                            StyledText {
                                Layout.fillWidth: true
                                text: appRow.modelData.name
                                font.pixelSize: Styling.fontSize(-2)
                                wrapMode: Text.WrapAnywhere
                            }
                            MetricAction {
                                readonly property var instance: appRow.modelData.instance
                                text: instance ? (root.closingId === instance.id ? "Closing…" : "Close") : "Focus"
                                enabled: instance ? (!closer.running && !!instance.id) : true
                                onClicked: {
                                    if (instance) root.closeApp(instance);
                                    else NiriService.focusWindow(appRow.modelData.windowId);
                                }
                                activeFocusOnTab: true
                                Accessible.role: Accessible.Button
                                Accessible.name: text + " " + appRow.modelData.name
                                Keys.onReturnPressed: clicked()
                                Keys.onSpacePressed: clicked()
                            }
                        }
                        StyledText {
                            Layout.fillWidth: true
                            text: appRow.modelData.detail
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
