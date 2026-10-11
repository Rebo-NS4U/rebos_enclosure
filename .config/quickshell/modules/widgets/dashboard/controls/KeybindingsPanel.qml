pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.config
import qs.modules.theme
import qs.modules.components

Item {
    id: root
    property int maxContentWidth: 480
    readonly property real layoutSpacing: Styling.fontSize(-3)
    property list<var> bindings: []
    property list<string> watchedFiles: []
    property string searchQuery: ""
    property string errorMessage: ""
    property bool refreshPending: false
    property var editingBinding: null
    property string editMessage: ""
    property bool editFailed: false
    property string saveRequest: ""

    function beginEdit(binding): void {
        if (writer.running)
            return;
        editingBinding = binding;
        editMessage = "";
        shortcutInput.text = binding.key;
        shortcutInput.forceActiveFocus();
        shortcutInput.selectAll();
    }

    function saveEdit(): void {
        if (!editingBinding || writer.running || !shortcutInput.text.trim())
            return;
        saveRequest = JSON.stringify({binding: editingBinding, key: shortcutInput.text});
        editMessage = "";
        writer.running = true;
    }
    readonly property list<var> filteredBindings: bindings.filter(binding => {
        const text = (binding.key + " " + binding.action + " " + binding.group).toLowerCase();
        return searchQuery.toLowerCase().trim().split(/\s+/).every(word => text.includes(word));
    })

    function refresh(): void {
        if (reader.running) {
            refreshPending = true;
            return;
        }
        reader.running = true;
    }

    Component.onCompleted: refresh()

    Process {
        id: writer
        command: ["python3", Quickshell.shellPath("scripts/edit_keybinding.py")]
        stdinEnabled: true
        onStarted: write(root.saveRequest + "\n")
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    root.editFailed = !result.ok;
                    root.editMessage = result.ok ? result.message : result.error;
                    if (result.ok) {
                        root.editingBinding = null;
                        root.refresh();
                    }
                } catch (error) {
                    root.editFailed = true;
                    root.editMessage = "Could not save the shortcut. Refresh the list and try again.";
                }
            }
        }
        onExited: (exitCode, exitStatus) => {
            root.saveRequest = "";
            if (exitCode !== 0) {
                root.editFailed = true;
                root.editMessage = "Could not save the shortcut. Refresh the list and try again.";
            }
        }
    }

    Process {
        id: reader
        command: ["python3", Quickshell.shellPath("scripts/list_keybindings.py")]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    root.bindings = result.bindings;
                    root.errorMessage = result.error;
                    // Keep FileView watchers alive across refreshes.
                    if (JSON.stringify(root.watchedFiles) !== JSON.stringify(result.files))
                        root.watchedFiles = result.files;
                } catch (error) {
                    root.errorMessage = "Could not read shortcuts. Try refreshing the list.";
                }
            }
        }
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0)
                root.errorMessage = "Could not read shortcuts. Try refreshing the list.";
            if (root.refreshPending) {
                root.refreshPending = false;
                refreshTimer.restart();
            }
        }
    }

    Timer {
        id: refreshTimer
        interval: 150
        onTriggered: root.refresh()
    }
    Repeater {
        model: root.watchedFiles
        delegate: Item {
            required property string modelData
            FileView {
                path: modelData
                preload: true
                watchChanges: true
                onFileChanged: {
                    reload();
                    refreshTimer.restart();
                }
            }
        }
    }

    component Caption: Text {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        font.family: Config.theme.font
        font.pixelSize: Styling.fontSize(-1)
        color: Colors.overSurfaceVariant
    }

    component Action: Button {
        id: button
        implicitHeight: Styling.fontSize(0) * 2.5
        background: StyledRect { variant: button.hovered ? "focus" : "common" }
        contentItem: Text {
            text: button.text
            color: button.enabled ? Colors.overSurface : Colors.overSurfaceVariant
            font.family: Config.theme.font
            font.pixelSize: Styling.fontSize(-1)
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: root.layoutSpacing

        PanelTitlebar {
            Layout.fillWidth: true
            title: "Keybindings"
            statusText: reader.running ? "Loading…" : root.bindings.length + " shortcuts"
            actions: [{
                icon: Icons.sync,
                tooltip: "Refresh shortcuts",
                enabled: !reader.running,
                onClicked: function () { root.refresh(); }
            }]
        }
        Caption {
            text: "Super is the Windows / logo key. Desktop shortcuts work throughout Niri; terminal shortcuts work in Kitty."
        }
        Caption {
            text: "Select Edit to change a shortcut while keeping its action. Changes are validated and backed up before saving. Kitty shows your configured mappings."
        }
        SearchInput {
            Layout.fillWidth: true
            placeholderText: "Find an action or shortcut…"
            onSearchTextChanged: text => root.searchQuery = text
        }
        StyledRect {
            Layout.fillWidth: true
            implicitHeight: editorLayout.implicitHeight + root.layoutSpacing * 2
            visible: root.editingBinding !== null
            variant: "pane"
            ColumnLayout {
                id: editorLayout
                anchors.fill: parent
                anchors.margins: root.layoutSpacing
                spacing: root.layoutSpacing / 2
                Caption {
                    text: (root.editingBinding?.action ?? "") + " · " + (root.editingBinding?.group ?? "")
                    color: Colors.overSurface
                    font.bold: true
                }
                RowLayout {
                    TextField {
                        id: shortcutInput
                        objectName: "shortcut-editor-input"
                        Layout.fillWidth: true
                        enabled: !writer.running
                        placeholderText: "Super+Shift+A"
                        font.family: Config.theme.font
                        font.pixelSize: Styling.fontSize(0)
                        color: Colors.overSurface
                        placeholderTextColor: Colors.overSurfaceVariant
                        selectionColor: Colors.primary
                        selectedTextColor: Colors.overPrimary
                        background: StyledRect { variant: "internalbg" }
                        onAccepted: root.saveEdit()
                    }
                    Action {
                        objectName: "shortcut-editor-save"
                        text: writer.running ? "Saving…" : "Save"
                        enabled: !writer.running && !!shortcutInput.text.trim()
                        onClicked: root.saveEdit()
                    }
                    Action {
                        text: "Cancel"
                        enabled: !writer.running
                        onClicked: {
                            root.editingBinding = null;
                            root.editMessage = "";
                        }
                    }
                }
                Caption { text: "Type modifiers separated by +, then a key name. Examples: Super+Shift+A, Ctrl+Shift+F, Alt+Return. Use 'plus' for the + key." }
            }
        }
        Caption {
            visible: root.editMessage !== ""
            text: root.editMessage
            color: root.editFailed ? Colors.error : Colors.primary
        }
        Caption {
            visible: root.errorMessage !== ""
            text: root.errorMessage
            color: Colors.error
        }
        Caption {
            visible: !reader.running && root.filteredBindings.length === 0
            text: root.bindings.length > 0 ? "No matching shortcuts." : "No configured shortcuts found."
        }

        ListView {
            id: shortcutList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: root.layoutSpacing / 2
            model: root.filteredBindings
            boundsBehavior: Flickable.StopAtBounds
            reuseItems: true
            ScrollBar.vertical: ScrollBar {}

            delegate: StyledRect {
                id: row
                required property var modelData
                width: shortcutList.width
                implicitHeight: rowLayout.implicitHeight + root.layoutSpacing * 2
                variant: hover.hovered ? "focus" : "pane"
                radius: Styling.radius(-2)

                RowLayout {
                    id: rowLayout
                    anchors.fill: parent
                    anchors.margins: root.layoutSpacing
                    spacing: root.layoutSpacing
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: root.layoutSpacing / 4
                        Text {
                            Layout.fillWidth: true
                            text: row.modelData.action
                            wrapMode: Text.WordWrap
                            color: Colors.overSurface
                            font.family: Config.theme.font
                            font.pixelSize: Styling.fontSize(0)
                        }
                        Caption {
                            text: row.modelData.group
                            font.pixelSize: Styling.fontSize(-2)
                        }
                    }
                    Text {
                        Layout.maximumWidth: shortcutList.width * 0.4
                        text: row.modelData.key
                        wrapMode: Text.WrapAnywhere
                        horizontalAlignment: Text.AlignRight
                        color: Colors.primary
                        font.family: Config.theme.font
                        font.pixelSize: Styling.fontSize(-1)
                        font.bold: true
                    }
                    Action {
                        text: "Edit"
                        enabled: !writer.running && (row.modelData.editable ?? false)
                        onClicked: root.beginEdit(row.modelData)
                    }
                }
                HoverHandler { id: hover }
                ToolTip.visible: hover.hovered
                ToolTip.text: row.modelData.source
            }
        }
    }
}
