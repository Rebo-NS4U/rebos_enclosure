pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.config

Singleton {
    id: root
    readonly property bool ready: Config.initialLoadComplete
    readonly property string mode: Config.performance.desktopBlur
    readonly property bool busy: applyProcess.running || debounce.running
    readonly property int strength: Config.performance.blurStrength
    property int requestedStrength: 50
    property string appliedMode: ""
    property string requestedMode: ""
    property string error: ""

    function schedule() {
        if (ready) debounce.restart();
    }
    onReadyChanged: schedule()
    onModeChanged: schedule()
    onStrengthChanged: schedule()
    Component.onCompleted: schedule()

    Timer {
        id: debounce
        interval: 120
        onTriggered: {
            if (applyProcess.running) return;
            root.requestedMode = root.mode;
            root.requestedStrength = root.strength;
            root.error = "";
            applyProcess.command = ["python3", Quickshell.shellDir + "/scripts/desktop_blur.py",
                root.requestedMode, Quickshell.env("HOME") + "/.cache/rebos_shell/niri-blur.kdl", String(root.requestedStrength)];
            applyProcess.running = true;
        }
    }
    Process {
        id: applyProcess
        stdout: StdioCollector { id: output }
        stderr: StdioCollector { id: errors }
        onExited: exitCode => {
            try {
                const result = JSON.parse(output.text);
                if (exitCode === 0 && result.ok) root.appliedMode = root.requestedMode;
                else root.error = result.error || "Could not apply blur settings.";
            } catch (_) {
                root.error = errors.text.trim() || "Could not apply blur settings.";
            }
            if (root.mode !== root.requestedMode || root.strength !== root.requestedStrength) root.schedule();
        }
    }
}
