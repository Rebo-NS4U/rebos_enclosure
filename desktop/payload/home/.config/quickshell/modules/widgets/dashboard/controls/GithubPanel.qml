pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.modules.components
import qs.modules.theme

Item {
    id: root
    objectName: "github-settings-panel"
    property int maxContentWidth: 760
    property var result: ({ message: "Not checked yet", local: "", remote: "", dirty: false })
    property string checkedAt: ""

    function check() {
        if (!checker.running)
            checker.running = true;
    }
    // The search indexer also instantiates panels, but has no visible area.
    onVisibleChanged: if (visible && width > 0 && checkedAt === "") check()
    onWidthChanged: if (visible && width > 0 && checkedAt === "") check()
    Component.onCompleted: if (visible && width > 0) check()

    Process {
        id: checker
        command: ["python3", Quickshell.shellPath("scripts/github_status.py")]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.result = JSON.parse(text);
                    root.checkedAt = new Date().toLocaleTimeString();
                } catch (e) {
                    root.result = { message: "Could not read update status", local: "", remote: "", dirty: false };
                }
            }
        }
        onExited: (code, status) => {
            if (code !== 0)
                root.result = { message: "Update check failed. Try again.", local: "", remote: "", dirty: false };
        }
    }

    Flickable {
        anchors.fill: parent
        clip: true
        contentHeight: column.implicitHeight + 40
        ColumnLayout {
            id: column
            width: Math.min(root.width, root.maxContentWidth)
            x: Math.max(0, (root.width - width) / 2)
            spacing: 12
            PanelTitlebar {
                title: "GitHub"
                description: "Desktop updates from Rebo-NS4U/rebos_enclosure."
            }
            SettingsGroup {
                title: "Update status"
                description: "Compare your installed version with the latest version on GitHub."
                StyledText {
                    Layout.fillWidth: true
                    text: checker.running ? "Checking GitHub…" : root.result.message
                    font.bold: true
                    wrapMode: Text.Wrap
                }
                StyledText {
                    Layout.fillWidth: true
                    visible: !!root.result.local
                    text: "Installed: " + (root.result.local || "").slice(0, 12)
                        + (root.result.remote ? "   •   GitHub: " + root.result.remote.slice(0, 12) : "")
                    color: Colors.overSurfaceVariant
                    wrapMode: Text.Wrap
                }
                StyledText {
                    Layout.fillWidth: true
                    visible: root.checkedAt !== ""
                    text: "Last checked: " + root.checkedAt
                    color: Colors.overSurfaceVariant
                }
                RowLayout {
                    spacing: 12
                    SettingsButton {
                        text: checker.running ? "Checking…" : "Check for updates"
                        enabled: !checker.running
                        onClicked: root.check()
                    }
                    SettingsButton {
                        text: "Open GitHub"
                        onClicked: Qt.openUrlExternally("https://github.com/Rebo-NS4U/rebos_enclosure")
                    }
                }
            }
        }
    }
}
