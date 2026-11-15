pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root
    property var release: ({available: false})
    property string feedback: ""
    readonly property bool running: launcher.running

    function check() {
        if (!checker.running) checker.running = true;
    }
    function apply() {
        if (!release.available || running) return;
        feedback = "Installing " + release.tag + "; see the update progress window.";
        launcher.command = ["kitty", "--title", "Enclosure release update", "python3",
            Quickshell.shellPath("scripts/github_update.py"), "--release", release.tag];
        launcher.started = false;
        launcher.running = true;
    }
    Timer {
        interval: 900000
        running: true
        triggeredOnStart: true
        repeat: true
        onTriggered: root.check()
    }
    Process {
        id: checker
        command: ["python3", Quickshell.shellPath("scripts/github_update.py"), "--check"]
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.release = JSON.parse(text); }
                catch (error) { root.release = {available: false}; }
            }
        }
        onExited: (code, status) => {
            if (code !== 0) root.release = {available: false};
        }
    }
    Process {
        id: launcher
        property bool started: false
        onStarted: started = true
        onExited: (code, status) => {
            root.feedback = code === 0 ? "Update window closed."
                : "Could not finish the update. Review the progress window or try again.";
            root.check();
        }
        onRunningChanged: {
            if (!running && !started) root.feedback = "Could not open the update progress window. Check that kitty is installed.";
        }
    }
}
