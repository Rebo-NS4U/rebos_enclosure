import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.components
import qs.modules.services
import qs.modules.theme
import qs.config

ColumnLayout {
    id: root
    spacing: 6
    property bool expanded: false
    readonly property var session: Ai.activeSession
    readonly property bool canSwitch: session.isDistill && !session.isBusy && !session.switchingSessionModel && !session.switchingDistillPreset
    onSessionChanged: expanded = false
    onVisibleChanged: {
        if (!visible)
            expanded = false;
    }

    Button {
        id: toggle
        objectName: "assistantPresetButton"
        Layout.fillWidth: true
        Layout.preferredHeight: 38
        padding: 10
        Accessible.name: "Choose Codex or a Distill preset"
        background: StyledRect {
            variant: toggle.hovered || root.expanded ? "focus" : "internalbg"
            radius: Styling.radius(8)
            border.width: 1
            border.color: Qt.alpha(Colors.primary, 0.25)
        }
        contentItem: RowLayout {
            spacing: 8
            StyledText {
                text: "Preset"
                color: Colors.outline
                font.pixelSize: Styling.fontSize(-2)
            }
            StyledText {
                Layout.fillWidth: true
                text: !root.session.isDistill ? "Codex + token saving" : root.session.switchingDistillPreset ? "Applying…" : root.session.distillPresetName
                elide: Text.ElideRight
                color: Colors.overSurface
                font.pixelSize: Styling.fontSize(-1)
                font.weight: Font.DemiBold
            }
            StyledText {
                text: root.expanded ? "▴" : "▾"
                color: Colors.primary
            }
        }
        StyledToolTip {
            show: toggle.hovered
            tooltipText: "Use Codex directly or choose a Distill preset"
        }
        onClicked: root.expanded = !root.expanded
    }

    StyledRect {
        Layout.fillWidth: true
        implicitHeight: Math.min(choices.implicitHeight + 20, root.Window.window ? Math.max(160, Math.min(330, root.Window.window.height * 0.4)) : 330)
        visible: root.expanded
        variant: "internalbg"
        radius: Styling.radius(8)
        Flickable {
            anchors.fill: parent
            anchors.margins: 10
            contentWidth: width
            contentHeight: choices.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            ColumnLayout {
                id: choices
                width: parent.width
                spacing: 5
                StyledText {
                    Layout.fillWidth: true
                    text: !root.session.isDistill ? "Codex uses RTK for compact command output and your existing Token Optimizer. Distill presets are optional." : root.session.isBusy ? "Change the preset after this reply finishes." : root.session.switchingDistillPreset ? "Waiting for Distill to confirm…" : "Saved separately for this chat."
                    wrapMode: Text.WordWrap
                    color: Colors.outline
                    font.pixelSize: Styling.fontSize(-2)
                }
                Button {
                    objectName: "assistantPreset_codex"
                    Layout.fillWidth: true
                    enabled: !root.session.isBusy && !root.session.switchingSessionModel && !root.session.switchingDistillPreset
                    text: "Codex + token saving" + (!root.session.isDistill ? "  ✓" : "")
                    contentItem: StyledText {
                        text: parent.text
                        color: Colors.overSurface
                        wrapMode: Text.WordWrap
                    }
                    background: StyledRect {
                        variant: !root.session.isDistill ? "focus" : "common"
                        radius: Styling.radius(4)
                    }
                    onClicked: {
                        if (root.session.isDistill) Ai.newSession("codex");
                        root.expanded = false;
                    }
                }
                StyledText {
                    Layout.fillWidth: true
                    text: "Changing between Codex and Distill opens a new chat. Your current chat stays available."
                    wrapMode: Text.WordWrap
                    color: Colors.outline
                    font.pixelSize: Styling.fontSize(-2)
                }
                Repeater {
                    model: root.session.distillPresets
                    delegate: Button {
                        id: choice
                        required property var modelData
                        objectName: "assistantPreset_" + modelData.id
                        Layout.fillWidth: true
                        implicitHeight: labels.implicitHeight + 16
                        padding: 8
                        enabled: root.canSwitch
                        readonly property bool selected: root.session.isDistill && modelData.id === root.session.distillPreset
                        Accessible.name: modelData.name + ". " + modelData.description
                        background: StyledRect {
                            variant: choice.selected ? "focus" : choice.hovered ? "common" : "transparent"
                            radius: Styling.radius(4)
                            border.width: choice.selected ? 1 : 0
                            border.color: Qt.alpha(Colors.primary, 0.4)
                        }
                        contentItem: ColumnLayout {
                            id: labels
                            spacing: 2
                            StyledText {
                                Layout.fillWidth: true
                                text: choice.modelData.name + (choice.selected ? "  ✓" : "")
                                color: Colors.overSurface
                                font.pixelSize: Styling.fontSize(-1)
                            }
                            StyledText {
                                Layout.fillWidth: true
                                text: choice.modelData.description
                                color: Colors.outline
                                wrapMode: Text.WordWrap
                                font.pixelSize: Styling.fontSize(-2)
                            }
                        }
                        onClicked: root.session.setDistillPreset(modelData.id)
                    }
                }
                StyledText {
                    Layout.fillWidth: true
                    visible: root.session.distillPresetError.length > 0
                    text: root.session.distillPresetError
                    wrapMode: Text.WordWrap
                    color: Colors.overSurface
                    font.pixelSize: Styling.fontSize(-2)
                }
                Button {
                    objectName: "assistantRefreshCodexAccount"
                    Layout.fillWidth: true
                    visible: !root.session.isDistill
                    enabled: !root.session.isBusy && !root.session.switchingSessionModel
                        && !root.session.statusText
                    text: "Use current Codex login"
                    contentItem: StyledText {
                        text: parent.text
                        color: Colors.overSurface
                        horizontalAlignment: Text.AlignHCenter
                    }
                    background: StyledRect {
                        variant: "focus"
                        radius: Styling.radius(4)
                    }
                    onClicked: {
                        root.session.refreshCodexAccount();
                        root.expanded = false;
                    }
                }
                Button {
                    objectName: "assistantStartDistill"
                    Layout.fillWidth: true
                    visible: !root.session.isDistill
                    text: "Start a Distill chat"
                    contentItem: StyledText {
                        text: parent.text
                        color: Colors.overSurface
                        horizontalAlignment: Text.AlignHCenter
                    }
                    background: StyledRect {
                        variant: "focus"
                        radius: Styling.radius(4)
                    }
                    onClicked: {
                        Ai.newSession("distill");
                        root.expanded = false;
                    }
                }
                Button {
                    objectName: "assistantConnectDistill"
                    Layout.fillWidth: true
                    visible: root.session.isDistill
                    enabled: !root.session.isBusy && !root.session.switchingDistillPreset && !root.session.switchingSessionModel && !root.session.connectingDistillAccount
                    text: root.session.connectingDistillAccount ? "Finish sign-in in your browser…" : "Connect ChatGPT"
                    contentItem: StyledText {
                        text: parent.text
                        color: Colors.overSurface
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                    background: StyledRect {
                        variant: "common"
                        radius: Styling.radius(4)
                    }
                    onClicked: root.session.connectDistillAccount()
                }
            }
        }
    }
}
