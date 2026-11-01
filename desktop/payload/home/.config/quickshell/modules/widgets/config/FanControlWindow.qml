pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.modules.components
import qs.modules.theme
import qs.modules.widgets.dashboard.controls

FloatingWindow {
    id: root
    title: "ThinkPad Fan Control"
    implicitWidth: 480
    implicitHeight: 360
    visible: false
    color: "transparent"
    property var reading: ({})
    property string message: ""
    property string output: ""
    property string errors: ""
    readonly property bool busy: action.running
    readonly property string fanState: reading.level === "auto" ? "Automatic" : reading.level === "0" ? (reading.speed === "0" ? "Fans off" : "Spinning down") : "Level " + (reading.level || "—")

    function change(mode: string): void {
        if (busy) return;
        output = "";
        errors = "";
        message = "Waiting for administrator approval…";
        action.command = ["python3", Quickshell.shellDir + "/scripts/thinkpad_fan.py", mode];
        action.running = true;
    }
    onVisibleChanged: if (visible) sample.running = true
    Timer { interval: 1000; repeat: true; running: root.visible; onTriggered: if (!sample.running) sample.running = true }
    Process {
        id: sample
        command: ["python3", Quickshell.shellDir + "/scripts/thinkpad_fan.py", "status"]
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.reading = JSON.parse(text); }
                catch (e) { root.reading = ({}); }
            }
        }
        onExited: (code, status) => { if (code !== 0) { root.reading = ({}); root.message = "ThinkPad fan status unavailable."; } }
    }
    Process {
        id: action
        stdout: StdioCollector { onStreamFinished: root.output = text.trim() }
        stderr: StdioCollector { onStreamFinished: root.errors = text.trim() }
        onExited: (code, status) => {
            root.message = code === 0 ? root.output : (root.errors || "Approval cancelled or fan change failed.");
            sample.running = true;
        }
    }
    IpcHandler {
        target: "fans"
        function open(): void { root.visible = true; }
        function close(): void { root.visible = false; }
        function status(): string { return JSON.stringify({visible: root.visible, busy: root.busy, reading: root.reading, message: root.message}); }
    }
    StyledRect {
        anchors.fill: parent
        variant: "bg"
        radius: Styling.radius(-2)
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 16
            RowLayout {
                Layout.fillWidth: true
                StyledText { text: "Cooling"; font.pixelSize: Styling.fontSize(6); font.bold: true; Layout.fillWidth: true }
                SettingsButton { text: "Close"; onClicked: root.visible = false }
            }
            SettingsGroup {
                title: "ThinkPad fans"
                RowLayout {
                    Layout.fillWidth: true
                    StyledText { text: root.fanState; color: Colors.primary; Layout.fillWidth: true }
                    StyledText { text: (root.reading.speed || "—") + " RPM"; font.pixelSize: Styling.fontSize(4); font.bold: true }
                }
                RowLayout {
                    Layout.fillWidth: true
                    SettingsButton { text: "Stop fans"; Layout.fillWidth: true; enabled: !root.busy && !!root.reading.level; onClicked: root.change("off") }
                    SettingsButton { text: "Automatic"; Layout.fillWidth: true; enabled: !root.busy && !!root.reading.level; onClicked: root.change("auto") }
                }
            }
            StyledText {
                Layout.fillWidth: true
                text: root.message || "Changes apply to this session. Closing this window keeps the selected mode."
                wrapMode: Text.WordWrap
                color: Colors.overSurfaceVariant
                font.pixelSize: Styling.fontSize(-1)
            }
            Item { Layout.fillHeight: true }
        }
    }
}
