pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
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
    readonly property string repository: "https://github.com/Rebo-NS4U/rebos_enclosure"
    readonly property color statusColor: checker.running ? Colors.primary
        : result.status === "error" ? Colors.error
        : result.status === "current" && !result.dirty ? Colors.success : Colors.warning
    readonly property string explanation: {
        switch (result.status) {
        case "current": return result.dirty
            ? "Your installed commit matches GitHub. Local edits mean some files differ from that published version."
            : "Your installed commit matches the latest commit on GitHub’s default branch.";
        case "behind": return "GitHub has newer commits available for your desktop.";
        case "ahead": return "This checkout contains commits that are not yet on GitHub’s default branch.";
        case "diverged": return "This checkout and GitHub both contain unique commits. Reconcile the two histories before updating.";
        case "unpublished": return "GitHub cannot compare this installed revision. It may contain unpublished commits or come from a different history.";
        case "error": return "The latest status could not be verified. Check your connection and try again; GitHub may also limit repeated requests.";
        default: return "Check your installed desktop against the official GitHub repository.";
        }
    }

    function dateLabel(value): string {
        if (!value) return "Date unavailable";
        const date = new Date(value);
        return isNaN(date.getTime()) ? value : date.toLocaleString();
    }
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
                    root.checkedAt = new Date().toLocaleString();
                } catch (e) {
                    root.result = { status: "error", message: "Could not read update status", local: "", remote: "", dirty: false };
                }
            }
        }
        onExited: (code, status) => {
            if (code !== 0)
                root.result = { status: "error", message: "Update check failed. Try again.", local: "", remote: "", dirty: false };
        }
    }

    component Detail: StyledText {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        color: Colors.overSurfaceVariant
    }

    Flickable {
        id: scroller
        anchors.fill: parent
        clip: true
        contentHeight: column.implicitHeight + 40
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}
        ColumnLayout {
            id: column
            width: Math.min(Math.max(0, root.width - 16), root.maxContentWidth)
            x: Math.max(0, (root.width - width) / 2)
            spacing: 12
            PanelTitlebar {
                title: "GitHub"
                description: "Version history and desktop updates from the official Enclosure repository."
            }
            SettingsGroup {
                title: "Update status"
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Rectangle {
                        width: 10; height: 10; radius: 5
                        color: root.statusColor
                    }
                    StyledText {
                        Layout.fillWidth: true
                        text: checker.running ? "Checking GitHub…" : root.result.message
                        color: root.statusColor
                        font.bold: true
                        wrapMode: Text.Wrap
                    }
                }
                Detail { text: root.explanation }
                Detail {
                    visible: root.result.ahead !== undefined && root.result.ahead !== null
                        && root.result.behind !== undefined && root.result.behind !== null
                    text: (root.result.ahead ?? "—") + " local commits ahead   •   "
                        + (root.result.behind ?? "—") + " commits behind GitHub"
                }
                Detail {
                    text: root.checkedAt ? "Last checked: " + root.checkedAt : "No completed check yet"
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    SettingsButton {
                        text: checker.running ? "Checking…" : "Check for updates"
                        enabled: !checker.running
                        onClicked: root.check()
                    }
                    SettingsButton {
                        text: "Open GitHub"
                        onClicked: Qt.openUrlExternally(root.repository)
                    }
                    SettingsButton {
                        text: "Compare versions"
                        visible: !!root.result.local && !!root.result.remote && root.result.local !== root.result.remote
                        enabled: !checker.running
                        onClicked: Qt.openUrlExternally(root.repository + "/compare/" + root.result.local + "..." + root.result.remote)
                    }
                }
            }
            SettingsGroup {
                title: "Repository & installation"
                Detail { text: "Repository: Rebo-NS4U/rebos_enclosure" }
                Detail { text: "Installation: " + (root.result.installation || "Not identified") }
                Detail { text: "Local branch: " + (root.result.branch || "Not available for this installation") }
                Detail { text: "GitHub default branch: " + (root.result.default_branch || "Not verified") }
                Detail {
                    visible: !!root.result.details_error
                    text: root.result.details_error || ""
                }
            }
            Repeater {
                model: [
                    { title: "Installed version", sha: root.result.local || "", info: root.result.local_commit || {} },
                    { title: "Latest on GitHub", sha: root.result.remote || "", info: root.result.remote_commit || {} }
                ]
                delegate: SettingsGroup {
                    id: revision
                    required property var modelData
                    title: modelData.title
                    StyledText {
                        Layout.fillWidth: true
                        text: revision.modelData.info.title || (revision.modelData.sha ? "Commit details unavailable" : "Version not identified")
                        font.bold: true
                        wrapMode: Text.Wrap
                    }
                    Detail { text: "Commit: " + (revision.modelData.sha || "Unknown") }
                    Detail {
                        visible: !!revision.modelData.info.author || !!revision.modelData.info.date
                        text: (revision.modelData.info.author || "Author unavailable") + "   •   " + root.dateLabel(revision.modelData.info.date)
                    }
                    SettingsButton {
                        text: "View commit on GitHub"
                        visible: !!revision.modelData.sha
                        onClicked: Qt.openUrlExternally(root.repository + "/commit/" + revision.modelData.sha)
                    }
                }
            }
            SettingsGroup {
                title: "Local changes"
                description: root.result.dirty
                    ? "Local edits are separate from commit sync status. Preserve them before applying an update."
                    : "Changes made after installing or committing your desktop."
                Detail {
                    text: root.result.change_count !== undefined && root.result.change_count !== null
                        ? root.result.change_count + " changed or untracked entries in this checkout"
                        : root.result.dirty ? "Local changes were recorded when this copy was installed."
                        : root.result.local ? "No local changes recorded for this installation." : "Local changes have not been verified."
                }
                Repeater {
                    model: root.result.changes || []
                    delegate: Detail {
                        required property var modelData
                        text: modelData.kind + " · " + modelData.path
                    }
                }
                Detail {
                    visible: (root.result.change_count || 0) > (root.result.changes || []).length
                    text: "Showing the first " + (root.result.changes || []).length + " entries."
                }
            }
            SettingsGroup {
                visible: (root.result.incoming || []).length > 0
                title: "Recent incoming commits"
                description: "Up to five recent commits from the GitHub comparison, newest first."
                Repeater {
                    model: root.result.incoming || []
                    delegate: ColumnLayout {
                        id: incoming
                        required property var modelData
                        Layout.fillWidth: true
                        StyledText {
                            Layout.fillWidth: true
                            text: incoming.modelData.title
                            font.bold: true
                            wrapMode: Text.Wrap
                        }
                        Detail {
                            text: incoming.modelData.sha.slice(0, 12) + " · " + incoming.modelData.author
                                + " · " + root.dateLabel(incoming.modelData.date)
                        }
                        SettingsButton {
                            text: "View commit"
                            onClicked: Qt.openUrlExternally(root.repository + "/commit/" + incoming.modelData.sha)
                        }
                    }
                }
            }
        }
    }
}
