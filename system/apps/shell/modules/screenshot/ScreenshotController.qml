import QtQuick
import Quickshell
import Quickshell.Io
import qs.modules.globals

Scope {
    id: root
    property bool exitOnClose: false
    property string imagePath: ""
    property string screenName: ""
    property string mode: "area"
    property string error: ""
    property bool opened: false
    property string helper: Qt.resolvedUrl("../../scripts/screenshot_editor.py").toString().replace("file://", "")
    function capture(requested) {
        if (captureProcess.running || exportProcess.running || opened || GlobalStates.lockscreenVisible) return;
        mode = requested;
        error = "";
        captureProcess.command = ["python3", helper, "capture", mode];
        captureProcess.running = true;
    }
    function close() {
        if (exportProcess.running) return;
        opened = false;
        if (imagePath) Quickshell.execDetached(["python3", helper, "clean", imagePath]);
        imagePath = "";
        if (exitOnClose) Qt.quit();
    }
    function exportImage(spec, action) {
        if (exportProcess.running) return;
        exportProcess.command = ["python3", helper, "export", imagePath, JSON.stringify(spec), action];
        exportProcess.running = true;
    }
    IpcHandler {
        target: "screenshot"
        function capture(mode: string): void { root.capture(mode); }
        function close(): void { root.close(); }
        function status(): string { return JSON.stringify({opened: root.opened, busy: captureProcess.running || exportProcess.running, error: root.error}); }
    }
    Process {
        id: captureProcess
        property string result: ""
        stdout: StdioCollector { onStreamFinished: captureProcess.result = text }
        stderr: StdioCollector { onStreamFinished: if (text.trim()) root.error = text.trim() }
        onExited: (code, status) => {
            if (code === 0) {
                try {
                    const data = JSON.parse(result);
                    root.imagePath = data.path;
                    root.screenName = data.screen;
                    root.opened = true;
                } catch (e) { root.error = String(e); }
            }
            if (!root.opened) {
                Quickshell.execDetached(["notify-send", "Screenshot failed", root.error || "Capture failed"]);
                if (root.exitOnClose) Qt.quit();
            }
        }
    }
    Process {
        id: exportProcess
        property string result: ""
        stdout: StdioCollector { onStreamFinished: exportProcess.result = text.trim() }
        stderr: StdioCollector { onStreamFinished: if (text.trim()) root.error = text.trim() }
        onExited: (code, status) => {
            if (code === 0) {
                root.close();
                Quickshell.execDetached(["notify-send", "Screenshot", result]);
            }
        }
    }
    Connections {
        target: GlobalStates
        function onLockscreenVisibleChanged() { if (GlobalStates.lockscreenVisible) root.close(); }
    }
    Variants {
        model: Quickshell.screens
        ScreenshotOverlay {
            required property ShellScreen modelData
            screen: modelData
            controller: root
            visible: root.opened && root.screenName === modelData.name && !GlobalStates.lockscreenVisible
            busy: exportProcess.running
        }
    }
}
