pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root
    property string disabled: ""
    property bool keyboardAvailable: false
    property bool touchscreenAvailable: false
    property string error: ""
    function toggle(kind) {
        if (helper.running)
            helper.write(kind + "\n");
    }
    function tooltip(kind) {
        const available = kind === "keyboard" ? keyboardAvailable : touchscreenAvailable;
        const label = kind === "keyboard" ? "Keyboard" : "Touchscreen";
        if (error) return error;
        if (!available) return label + ": unavailable";
        if (disabled === kind) return label + ": Off · tap to enable";
        if (disabled !== "") return label + ": On · enable the other input first";
        return label + ": On · tap to disable";
    }
    Process {
        id: helper
        command: ["python3", Quickshell.shellPath("scripts/input_guard.py")]
        running: true
        stdinEnabled: true
        stdout: SplitParser {
            onRead: data => {
                try {
                    const state = JSON.parse(data);
                    root.disabled = state.disabled;
                    root.keyboardAvailable = state.keyboard;
                    root.touchscreenAvailable = state.touchscreen;
                    root.error = state.error;
                } catch (e) { root.error = "Cannot read input state"; }
            }
        }
        onExited: {
            root.disabled = "";
            root.keyboardAvailable = false;
            root.touchscreenAvailable = false;
            root.error = "Input control unavailable";
        }
    }
}
