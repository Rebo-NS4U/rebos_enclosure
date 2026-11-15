import QtQuick
import Quickshell
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.theme
import qs.modules.components
import qs.config
import qs.modules.widgets.dashboard.controls

Item {
    id: root
    property int maxContentWidth: 760
    readonly property int contentWidth: Math.min(width, maxContentWidth)
    readonly property real sideMargin: Math.max(0, (width - contentWidth) / 2)
    Flickable {
        anchors.fill: parent
        clip: true
        contentHeight: contentColumn.implicitHeight + 24
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}
        ColumnLayout {
            id: contentColumn
            width: root.contentWidth
            x: root.sideMargin
            spacing: 16
            PanelTitlebar {
                title: "Assistant"
                description: "Manage the assistant and its default working folder."
            }
            SettingsGroup {
                title: "Availability"
                description: "Uses your existing Codex login."
                SettingsToggleRow {
                    objectName: "assistant-enabled"
                    label: "Enable assistant"
                    description: "Allow the assistant to start when needed."
                    checked: Config.ai.enabled ?? true
                    onToggled: checked => Config.ai.enabled = checked
                }
                StyledText {
                    visible: !(Config.ai.enabled ?? true)
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: "The assistant is disabled."
                    color: Colors.overSurfaceVariant
                }
            }
            SettingsGroup {
                title: "Working folder"
                description: "New chats start here. Leave empty to use your home folder."
                enabled: Config.ai.enabled ?? true
                opacity: enabled ? 1 : 0.5
                SettingsTextField {
                    objectName: "assistant-working-folder"
                    Layout.fillWidth: true
                    Accessible.name: "Default working folder"
                    text: Config.ai?.workingDirectory ?? ""
                    placeholderText: "~/code/project"
                    onEditingFinished: {
                        if (Config.ai && Config.ai.workingDirectory !== text)
                            Config.setAiWorkingDirectory(text);
                    }
                }
                SettingsButton {
                    text: "Open assistant"
                    onClicked: Quickshell.execDetached([Quickshell.env("HOME") + "/.local/bin/rebos-assistant"])
                }
            }
        }
    }
}
