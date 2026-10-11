import QtQuick
import Quickshell.Io

// Serialize each app's writes, retaining only the newest pending palette.
QtObject {
    id: root
    property list<string> pendingCommand: []

    function submit(command: list<string>): void {
        pendingCommand = command;
        if (!process.running)
            startNext();
    }

    function startNext(): void {
        if (pendingCommand.length === 0)
            return;
        process.command = pendingCommand;
        pendingCommand = [];
        process.running = true;
    }

    property Process process: Process {
        id: process
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0)
                console.warn("Theme writer failed:", exitCode);
            Qt.callLater(root.startNext);
        }
        stderr: StdioCollector {
            onStreamFinished: {
                if (text.trim())
                    console.warn("Theme writer:", text.trim());
            }
        }
    }
}
