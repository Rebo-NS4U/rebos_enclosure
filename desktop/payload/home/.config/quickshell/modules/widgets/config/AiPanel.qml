import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.theme
import qs.modules.components
import qs.modules.services
import qs.config
import qs.modules.widgets.dashboard.controls

Item {
    id: root

    property int maxContentWidth: 760
    readonly property int contentWidth: Math.min(width, maxContentWidth)
    readonly property real sideMargin: Math.max(0, (width - contentWidth) / 2)

    Flickable {
        anchors.fill: parent
        contentHeight: contentColumn.implicitHeight + 40
        clip: true
        bottomMargin: 40

        ColumnLayout {
            id: contentColumn
            width: root.contentWidth
            x: root.sideMargin
            spacing: 12

            PanelTitlebar {
                title: "Assistant"
                description: "Connection, working folder and current session."
            }

            StyledText {
                Layout.fillWidth: true
                text: "Uses your existing Codex login."
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(-1)
                color: Colors.outline
                wrapMode: Text.Wrap
            }

            StyledRect {
                Layout.fillWidth: true
                implicitHeight: 64
                variant: "common"
                radius: Styling.radius(-2)
                border.width: 1
                border.color: Qt.alpha(Colors.outline, 0.3)

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        StyledText {
                            text: "Enable assistant"
                            font.family: Config.theme.font
                            font.pixelSize: Styling.fontSize(1)
                            font.weight: Font.Bold
                            color: Colors.overSurface
                        }

                        StyledText {
                            Layout.fillWidth: true
                            text: "Start the assistant when needed."
                            font.family: Config.theme.font
                            font.pixelSize: Styling.fontSize(-2)
                            color: Colors.outline
                            wrapMode: Text.Wrap
                        }
                    }

                    StyledSwitch {
                        id: aiEnabledSwitch
                        checked: Config.ai.enabled ?? true
                        onToggled: Config.ai.enabled = checked


                    }
                }
            }

            StyledText {
                Layout.fillWidth: true
                visible: !(Config.ai.enabled ?? true)
                text: "AI is disabled. Codex will not start."
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(-1)
                color: Colors.outline
                wrapMode: Text.Wrap
            }

            StyledRect {
                Layout.fillWidth: true
                implicitHeight: workingDirectoryColumn.implicitHeight + 32
                variant: "common"
                radius: Styling.radius(-2)
                border.width: 1
                border.color: Qt.alpha(Colors.outline, 0.3)
                enabled: Config.ai.enabled ?? true
                opacity: enabled ? 1 : 0.5

                ColumnLayout {
                    id: workingDirectoryColumn
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 8

                    StyledText {
                        text: "Working folder"
                        font.family: Config.theme.font
                        font.pixelSize: Styling.fontSize(1)
                        font.weight: Font.Bold
                        color: Colors.overSurface
                    }

                    StyledText {
                        Layout.fillWidth: true
                        text: "New chats start in this folder. Leave empty to use your home folder."
                        font.family: Config.theme.font
                        font.pixelSize: Styling.fontSize(-2)
                        color: Colors.outline
                        wrapMode: Text.Wrap
                    }

                    SettingsTextField {
                        id: workingDirectoryInput
                        Layout.fillWidth: true
                        text: Config.ai && Config.ai.workingDirectory ? Config.ai.workingDirectory : ""
                        placeholderText: "~/code/project"
                        color: Colors.overSurface
                        font.family: Config.theme.font
                        onEditingFinished: {
                            if (Config.ai && Config.ai.workingDirectory !== text)
                                Config.setAiWorkingDirectory(text);
                        }


                    }
                }
            }

            StyledText {
                Layout.fillWidth: true
                text: "Connection"
                visible: Config.ai.enabled ?? true
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(4)
                font.weight: Font.Bold
                color: Colors.overSurface
            }

            Repeater {
                model: (Config.ai.enabled ?? true) ? Ai.activeSession.models : []

                delegate: StyledRect {
                    id: agentCard
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: agentColumn.implicitHeight + 32
                    variant: Ai.activeSession.currentAgentId === modelData.id ? "focus" : "surface"
                    radius: Styling.radius(-2)
                border.width: 1
                border.color: Qt.alpha(Colors.outline, 0.3)

                    ColumnLayout {
                        id: agentColumn
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Image {
                                Layout.preferredWidth: 24
                                Layout.preferredHeight: 24
                                source: modelData.icon || ""
                                fillMode: Image.PreserveAspectFit
                                mipmap: true
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1

                                StyledText {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    font.family: Config.theme.font
                                    font.pixelSize: Styling.fontSize(2)
                                    font.weight: Font.Bold
                                    color: Colors.overSurface
                                }

                                StyledText {
                                    Layout.fillWidth: true
                                    text: modelData.description || ""
                                    font.family: Config.theme.font
                                    font.pixelSize: Styling.fontSize(-2)
                                    color: Colors.outline
                                    wrapMode: Text.Wrap
                                }
                            }

                            StyledText {
                                text: Ai.activeSession.currentAgentId === modelData.id
                                    ? (Ai.activeSession.sessionReady ? "Connected" : "Selected") : ""
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(-2)
                                color: Ai.activeSession.sessionReady && Ai.activeSession.currentAgentId === modelData.id
                                    ? Colors.success : Styling.srItem("overprimary")
                            }
                        }

                        StyledRect {
                            Layout.fillWidth: true
                            implicitHeight: commandText.implicitHeight + 16
                            variant: "internalbg"
                            radius: Styling.radius(4)

                            StyledText {
                                id: commandText
                                anchors.fill: parent
                                anchors.margins: 8
                                text: modelData.command.join(" ")
                                font.family: "Monospace"
                                font.pixelSize: Styling.fontSize(-2)
                                color: Colors.outline
                                wrapMode: Text.WrapAnywhere
                            }
                        }

                        StyledText {
                            Layout.fillWidth: true
                            text: modelData.installHint || ""
                            font.family: Config.theme.font
                            font.pixelSize: Styling.fontSize(-2)
                            color: Colors.outline
                            wrapMode: Text.Wrap
                        }

                        RowLayout {
                            Layout.alignment: Qt.AlignRight
                            spacing: 8

                            SettingsButton {
                                visible: Ai.activeSession.currentAgentId === modelData.id
                                text: "Reconnect"
                                flat: true
                                onClicked: Ai.activeSession.reconnectAgent()

                                background: StyledRect {
                                    variant: parent.hovered ? "focus" : "pane"
                                    radius: Styling.radius(4)
                                }

                                contentItem: StyledText {
                                    text: parent.text
                                    color: Colors.overSurface
                                    font.family: Config.theme.font
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }

                            SettingsButton {
                                text: Ai.activeSession.currentAgentId === modelData.id ? "Active" : "Connect"
                                enabled: Ai.activeSession.currentAgentId !== modelData.id
                                flat: true
                                onClicked: Ai.activeSession.setModel(modelData.id)

                                background: StyledRect {
                                    variant: parent.enabled ? "primary" : "pane"
                                    radius: Styling.radius(4)
                                    opacity: parent.enabled ? 1 : 0.6
                                }

                                contentItem: StyledText {
                                    text: parent.text
                                    color: parent.enabled ? Colors.overPrimary : Colors.outline
                                    font.family: Config.theme.font
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }
                    }
                }
            }

            StyledRect {
                Layout.fillWidth: true
                visible: (Config.ai.enabled ?? true) && Ai.activeSession.currentSessionModelId.length > 0
                implicitHeight: activeSessionColumn.implicitHeight + 32
                variant: "common"
                radius: Styling.radius(-2)
                border.width: 1
                border.color: Qt.alpha(Colors.outline, 0.3)

                ColumnLayout {
                    id: activeSessionColumn
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 6

                    StyledText {
                        text: "Current session"
                        font.family: Config.theme.font
                        font.pixelSize: Styling.fontSize(1)
                        font.weight: Font.Bold
                        color: Colors.overSurface
                    }

                    StyledText {
                        Layout.fillWidth: true
                        text: "Model: " + (Ai.activeSession.currentSessionModelId || "agent default")
                            + (Ai.activeSession.currentModeId ? "\nMode: " + Ai.activeSession.currentModeId : "")
                        font.family: "Monospace"
                        font.pixelSize: Styling.fontSize(-2)
                        color: Colors.outline
                        wrapMode: Text.WrapAnywhere
                    }
                }
            }
        }
    }
}
