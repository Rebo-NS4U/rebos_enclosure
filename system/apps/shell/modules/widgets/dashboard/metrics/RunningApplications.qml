pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.modules.components
import qs.modules.theme
import qs.modules.services

StyledRect {
    id: root
    property var instances: []
    readonly property var applications: applicationRows(NiriService.rawWindows, instances)
    property string status: "Loading…"
    property string output: ""
    property string closingId: ""
    property string actionMessage: ""
    property var pendingCloseCommands: []
    property bool closeFailed: false

    function applicationRows(windows, shellInstances) {
        const shellPids = new Set(shellInstances.map(app => app.pid));
        const rows = shellInstances.map(app => ({
            key: "quickshell:" + app.id,
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
                existing.ids.push(window.id);
                if (window.is_focused) existing.window = window;
            } else {
                windowApps.set(key, { window: window, ids: [window.id] });
            }
        }
        for (const [key, {window, ids}] of windowApps) {
            rows.push({
                key: "window:" + key,
                name: DesktopEntries.byId(window.app_id || "")?.name
                    || window.app_id || window.title || "Unknown application",
                detail: ids.length > 1 ? ids.length + " windows" : (window.title || "1 window"),
                windowId: window.id,
                windowIds: ids
            });
        }
        return rows.sort((a, b) => a.name.localeCompare(b.name));
    }

    function closeApp(app) {
        if (closingId !== "") return;
        // Target instance and window IDs so a focus change cannot redirect a close.
        pendingCloseCommands = app.instance
            ? [["qs", "kill", "--id", app.instance.id]]
            : app.windowIds.map(id => ["niri", "msg", "action", "close-window", "--id", String(id)]);
        closingId = app.key;
        actionMessage = "";
        closeFailed = false;
        closeNext();
    }

    function closeNext() {
        if (pendingCloseCommands.length > 0) {
            closer.command = pendingCloseCommands.shift();
            closer.running = true;
        } else {
            actionMessage = closeFailed ? "Some close requests failed. The app or window may have already exited." : "Close requested.";
            closingId = "";
            refresh();
        }
    }

    Process {
        id: closer
        onExited: (exitCode, exitStatus) => {
            root.closeFailed = root.closeFailed || exitCode !== 0;
            Qt.callLater(root.closeNext);
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
            Layout.preferredHeight: Math.min(appList.implicitHeight, Styling.spacing(280))
            visible: root.applications.length > 0
            clip: true
            contentWidth: availableWidth
            ScrollBar.vertical.policy: appList.implicitHeight > availableHeight ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
            ColumnLayout {
                id: appList
                width: parent.width
                spacing: Styling.spacing(6)
                Repeater {
                    model: root.applications
                    ColumnLayout {
                        id: appRow
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: Styling.spacing(4)
                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                StyledText {
                                    Layout.fillWidth: true
                                    text: appRow.modelData.name
                                    font.bold: true
                                    font.pixelSize: Styling.fontSize(-2)
                                    elide: Text.ElideRight
                                }
                                StyledText {
                                    Layout.fillWidth: true
                                    text: appRow.modelData.detail
                                    font.pixelSize: Styling.fontSize(-3)
                                    color: Colors.overSurfaceVariant
                                    elide: Text.ElideRight
                                    HoverHandler { id: detailHover }
                                    ToolTip.visible: truncated && detailHover.hovered
                                    ToolTip.text: text
                                }
                            }
                            MetricAction {
                                visible: !appRow.modelData.instance
                                text: "Focus"
                                Accessible.name: "Focus " + appRow.modelData.name
                                onClicked: NiriService.focusWindow(appRow.modelData.windowId)
                            }
                            MetricAction {
                                text: root.closingId === appRow.modelData.key ? "Closing…" : "Close"
                                enabled: root.closingId === "" && (!appRow.modelData.instance || !!appRow.modelData.instance.id)
                                onClicked: root.closeApp(appRow.modelData)
                                activeFocusOnTab: true
                                Accessible.role: Accessible.Button
                                Accessible.name: "Close " + appRow.modelData.name
                                Keys.onReturnPressed: clicked()
                                Keys.onSpacePressed: clicked()
                            }
                        }
                        Separator {
                            Layout.fillWidth: true
                            implicitHeight: 1
                        }
                    }
                }
            }
        }
    }
}
