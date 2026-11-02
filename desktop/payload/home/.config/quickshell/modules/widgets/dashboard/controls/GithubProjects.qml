pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.modules.components
import qs.modules.theme

ColumnLayout {
    id: root
    objectName: "github-project-controls"
    default property alias overview: overviewSlot.data
    Layout.fillWidth: true
    property var project: ({})
    property string selectedPath: ""
    property bool checking: false
    property bool initialized: false
    property var projects: []
    property var repositories: []
    property var selectedFiles: []
    property string desktopPath: ""
    property string mode: ""
    property string requestText: ""
    property string feedback: ""
    property bool failed: false
    property var pending: ({})
    readonly property string activePath: selectedPath || desktopPath
    readonly property bool busy: worker.running || checking
    readonly property bool canEdit: activePath !== "" && !busy && project.path === activePath
    signal projectSelected(string path)
    signal refreshRequested()

    onProjectChanged: {
        const available = (project.all_changes || []).map(c => c.path).concat(project.staged || []);
        selectedFiles = selectedFiles.filter(p => available.includes(p));
    }
    function start(command) {
        if (busy) return;
        mode = command;
        worker.command = ["python3", Quickshell.shellPath("scripts/github_projects.py"), command];
        if (command !== "catalog") feedback = "";
        worker.running = true;
    }
    function initialize() {
        if (!initialized && visible && width > 0 && !busy) {
            initialized = true;
            start("catalog");
        }
    }
    onVisibleChanged: initialize()
    onWidthChanged: initialize()
    onBusyChanged: if (!busy) initialize()
    Component.onCompleted: initialize()

    function act(action, fields, confirm) {
        if (busy) return;
        const payload = Object.assign({ action: action, path: activePath }, fields || {});
        pending = payload;
        if (confirm) {
            confirmation.open();
        } else {
            requestText = JSON.stringify(payload);
            start("action");
        }
    }
    function toggleFile(path, checked) {
        selectedFiles = checked ? selectedFiles.concat([path]) : selectedFiles.filter(p => p !== path);
    }
    function load(text) {
        try {
            const data = JSON.parse(text);
            failed = data.ok === false;
            if (failed) { feedback = data.message || "Project request failed."; return; }
            if (mode === "catalog") {
                desktopPath = data.desktop_path || "";
                projects = [{ label: "Enclosure", path: "" }].concat(
                    (data.projects || []).filter(p => p.path !== root.desktopPath));
            } else if (mode === "remote") {
                repositories = data.repositories || [];
                feedback = repositories.length + " GitHub repositories loaded. Select one or enter owner/repository below.";
            } else {
                feedback = data.message + (data.output ? "\n" + data.output : "");
                if (data.refresh === false) return;
                if (pending.action === "commit") commitMessage.text = "";
                if (data.path && (data.path !== activePath || pending.action === "clone" || pending.action === "add"))
                    root.projectSelected(data.path);
                else
                    root.refreshRequested();
                catalogRefresh.restart();
            }
        } catch (e) { failed = true; feedback = "Could not read project response."; }
    }
    Timer { id: catalogRefresh; interval: 300; onTriggered: { if (!root.busy) root.start("catalog"); else restart(); } }
    Process {
        id: worker
        stdinEnabled: true
        onStarted: if (root.mode === "action") write(root.requestText + "\n")
        stdout: StdioCollector { onStreamFinished: root.load(text) }
        onExited: (code, status) => {
            if (code !== 0) { root.failed = true; root.feedback = "Project process failed. Try again."; }
        }
    }
    component Caption: StyledText { Layout.fillWidth: true; wrapMode: Text.Wrap; color: Colors.overSurfaceVariant }
    component Field: SettingsTextField { Layout.fillWidth: true }

    SettingsGroup {
        title: "Projects"
        description: "Manage local checkouts and access repositories through your GitHub CLI login."
        SettingsComboBox {
            Layout.fillWidth: true
            model: root.projects
            textRole: "label"
            enabled: !root.busy
            currentIndex: Math.max(0, root.projects.findIndex(p => p.path === root.selectedPath))
            onActivated: root.projectSelected(root.projects[currentIndex].path)
        }
        Caption { text: root.activePath ? "Local folder: " + root.activePath : "Select or add a local checkout to use Git controls." }
        Field { id: localPath; placeholderText: "Existing project folder, e.g. ~/code/project"; enabled: !root.busy }
        Flow {
            Layout.fillWidth: true; spacing: 8
            SettingsButton { text: "Add local project"; enabled: !root.busy && localPath.text.trim() !== ""; onClicked: { root.pending = {action: "add"}; root.act("add", {path: localPath.text}, false); } }
            SettingsButton { text: "Refresh projects"; enabled: !root.busy; onClicked: root.start("catalog") }
            SettingsButton { text: "Browse my GitHub projects"; enabled: !root.busy; onClicked: root.start("remote") }
            SettingsButton { text: "Open folder"; enabled: !!root.activePath; onClicked: Qt.openUrlExternally("file://" + root.activePath) }
            SettingsButton { text: "Open terminal"; enabled: !!root.activePath; onClicked: Quickshell.execDetached(["kitty", "--directory", root.activePath]) }
        }
        SettingsComboBox {
            Layout.fillWidth: true
            visible: root.repositories.length > 0
            model: root.repositories
            textRole: "nameWithOwner"
            enabled: !root.busy
            onActivated: {
                repositoryName.text = root.repositories[currentIndex].nameWithOwner;
                cloneDestination.text = "~/code/" + repositoryName.text.split("/").pop();
            }
        }
        Field { id: repositoryName; placeholderText: "GitHub owner/repository or URL"; enabled: !root.busy }
        Field { id: cloneDestination; placeholderText: "New clone folder, e.g. ~/code/project"; enabled: !root.busy }
        Flow {
            Layout.fillWidth: true; spacing: 8
            SettingsButton {
                text: "Clone project"
                enabled: !root.busy && repositoryName.text.trim() !== "" && cloneDestination.text.trim() !== ""
                onClicked: { root.pending = {action: "clone"}; root.act("clone", {repository: repositoryName.text, destination: cloneDestination.text}, false); }
            }
            SettingsButton {
                text: "View repository"
                enabled: repositoryName.text.trim() !== ""
                onClicked: {
                    const name = repositoryName.text.trim().replace(/^https:\/\/github.com\//, "").replace(/^git@github.com:/, "").replace(/\.git$/, "");
                    if (/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(name)) Qt.openUrlExternally("https://github.com/" + name);
                }
            }
            SettingsButton { text: "GitHub login in terminal"; enabled: !root.busy; onClicked: Quickshell.execDetached(["kitty", "gh", "auth", "login", "--web", "--hostname", "github.com"]) }
        }
    }
    ColumnLayout { id: overviewSlot; Layout.fillWidth: true; spacing: 12 }
    SettingsGroup {
        title: "Git controls"
        description: "Actions apply to the selected local project. Pull requires a clean checkout and fast-forwards only."
        enabled: root.canEdit
        Caption { text: "Branch: " + (root.project.branch || "Unknown") + "   •   Tracks: " + (root.project.upstream || "No upstream") }
        Flow {
            Layout.fillWidth: true; spacing: 8
            SettingsButton { text: "Fetch origin"; onClicked: root.act("fetch", {}, false) }
            SettingsButton { text: "Pull current branch"; onClicked: root.act("pull", {}, false) }
            SettingsButton { text: "Push current branch"; onClicked: root.act("push", {}, true) }
            SettingsButton { text: "Issues"; onClicked: Qt.openUrlExternally(root.project.repository + "/issues") }
            SettingsButton { text: "Pull requests"; onClicked: Qt.openUrlExternally(root.project.repository + "/pulls") }
        }
        SettingsComboBox {
            id: branches
            Layout.fillWidth: true
            model: root.project.branches || []
            currentIndex: Math.max(0, (root.project.branches || []).indexOf(root.project.branch))
        }
        SettingsButton { text: "Switch to selected branch"; enabled: branches.count > 0; onClicked: root.act("switch", {branch: branches.currentText}, false) }
        Field { id: newBranch; placeholderText: "New branch name" }
        SettingsButton { text: "Create and switch branch"; enabled: newBranch.text.trim() !== ""; onClicked: root.act("branch", {branch: newBranch.text}, false) }
    }
    SettingsGroup {
        title: "Stage & commit"
        description: "Select individual files. Commit includes only the selected staged files; other staged work stays in place."
        enabled: root.canEdit
        Caption { text: root.selectedFiles.length + " selected   •   " + (root.project.staged || []).length + " staged" }
        Field { id: fileSearch; placeholderText: "Filter changed files (shows up to 100 matching entries)" }
        // Include staged rename source paths so both sides can be selected.
        Repeater {
            model: {
                const changes = root.project.all_changes || [];
                const known = changes.map(c => c.path);
                return changes.concat((root.project.staged || []).filter(p => !known.includes(p)).map(p => ({path: p, kind: "Staged"}))).filter(c => c.path.toLowerCase().includes(fileSearch.text.toLowerCase())).slice(0, 100);
            }
            delegate: CheckBox {
                id: fileChoice
                required property var modelData
                Layout.fillWidth: true
                checked: root.selectedFiles.includes(modelData.path)
                onToggled: root.toggleFile(modelData.path, checked)
                contentItem: Caption {
                    leftPadding: fileChoice.indicator.width + fileChoice.spacing
                    text: ((root.project.staged || []).includes(fileChoice.modelData.path) ? "Staged · " : "")
                        + fileChoice.modelData.kind + " · " + fileChoice.modelData.path
                }
            }
        }
        Flow {
            Layout.fillWidth: true; spacing: 8
            SettingsButton { text: "View selected diff"; enabled: root.selectedFiles.length > 0; onClicked: root.act("diff", {files: root.selectedFiles}, false) }
            SettingsButton { text: "Stage selected"; enabled: root.selectedFiles.length > 0; onClicked: root.act("stage", {files: root.selectedFiles}, false) }
            SettingsButton { text: "Unstage selected"; enabled: root.selectedFiles.length > 0; onClicked: root.act("unstage", {files: root.selectedFiles}, false) }
        }
        Field { id: commitMessage; placeholderText: "Commit message" }
        SettingsButton { text: "Commit selected staged files…"; enabled: root.selectedFiles.length > 0 && commitMessage.text.trim() !== ""; onClicked: root.act("commit", {files: root.selectedFiles, message: commitMessage.text}, true) }
    }
    SettingsGroup {
        title: "Create pull request"
        description: "Push your branch first, then create a pull request against the chosen base."
        enabled: root.canEdit
        Field { id: prBase; placeholderText: "Base branch"; text: root.project.default_branch || "" }
        Field { id: prTitle; placeholderText: "Pull request title" }
        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: 110
            TextArea {
                id: prBody
                placeholderText: "Pull request description"
                wrapMode: TextEdit.Wrap
                selectByMouse: true
                color: Colors.overSurface
                placeholderTextColor: Colors.overSurfaceVariant
                background: StyledRect { variant: "internalbg" }
            }
        }
        CheckBox { id: draft; text: "Create as draft"; checked: true; palette.windowText: Colors.overSurface }
        SettingsButton { text: "Create pull request…"; enabled: prTitle.text.trim() !== "" && prBase.text.trim() !== ""; onClicked: root.act("pr", {title: prTitle.text, body: prBody.text, base: prBase.text, draft: draft.checked}, true) }
    }
    SettingsGroup {
        visible: worker.running || root.feedback !== ""
        title: "Action result"
        Caption { text: worker.running ? "Working on " + root.activePath + "…" : root.feedback; color: root.failed ? Colors.error : Colors.overSurfaceVariant }
    }
    Dialog {
        id: confirmation
        parent: Overlay.overlay
        modal: true
        title: "Review GitHub action"
        width: Math.min(560, (parent?.width || 700) - 40)
        x: ((parent?.width || width) - width) / 2
        y: ((parent?.height || height) - height) / 2
        background: StyledRect { variant: "popup" }
        contentItem: ColumnLayout {
            Caption { text: "Action: " + (root.pending.action || "") + "\nRepository: " + (root.project.repository_name || root.project.repository || "") + "\nFolder: " + (root.pending.path || "") + "\nBranch: " + (root.project.branch || "") }
            Caption { visible: !!root.pending.message; text: "Commit message: " + (root.pending.message || "") }
            Caption { visible: !!root.pending.files; text: "Files (" + (root.pending.files || []).length + "):\n" + (root.pending.files || []).slice(0, 12).join("\n")
                + ((root.pending.files || []).length > 12 ? "\n… and " + (root.pending.files.length - 12) + " more selected files" : "") }
            Caption { visible: root.pending.action === "push"; text: "Publishes commits on this branch to origin. Uncommitted edits are not included." }
            Caption { visible: root.pending.action === "pr"; text: "Title: " + (root.pending.title || "") + "\nBase: " + (root.pending.base || "") + "\nDraft: " + (root.pending.draft ? "Yes" : "No") + "\n" + (root.pending.body || "") }
            RowLayout {
                SettingsButton { text: "Cancel"; onClicked: confirmation.close() }
                SettingsButton { text: "Confirm " + (root.pending.action || "action"); onClicked: { confirmation.close(); root.requestText = JSON.stringify(root.pending); root.start("action"); } }
            }
        }
    }
}
