pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.config
import qs.modules.components
import qs.modules.theme
import qs.modules.services
import "../../../theme/ShellStyles.js" as ShellStyles

SettingsGroup {
    id: root
    title: "Theme style"
    description: "Choose a shared appearance for the shell and supported apps."
    property string settingsSection: "style"

    StyledText {
        Layout.fillWidth: true
        text: "Set backgrounds and colors for the shell, bar, Fish and supported apps. Adjust fonts and corners, transparency, blur and motion in Appearance. Terminal text follows the monospace font settings."
        wrapMode: Text.WordWrap
        font.pixelSize: Styling.fontSize(-1)
        color: Colors.overSurfaceVariant
    }
    GridLayout {
        columns: root.width < Styling.fontSize(0) * 26 ? 1 : 2
        Layout.fillWidth: true
        columnSpacing: Styling.spacing(10)
        rowSpacing: Styling.spacing(10)
        Repeater {
            model: ShellStyles.styles
            delegate: Button {
                id: card
                required property var modelData
                objectName: "shell-style-" + modelData.id
                readonly property bool selected: Styling.shellStyle === modelData.id
                readonly property var sample: Styling.styleConfig(modelData.id, "bg")
                Layout.fillWidth: true
                implicitHeight: Styling.fontSize(0) * 14
                padding: 12
                onClicked: {
                    Config.theme.shellStyle = modelData.id;
                    if (modelData.id === "frosted") {
                        Config.theme.shellTransparency = -1;
                        if (Config.performance.desktopBlur === "off") Config.performance.desktopBlur = "shell";
                    }
                }
                background: StyledRect {
                    variant: card.hovered ? "focus" : "common"
                    radius: Styling.radius(-2)
                    border.width: card.selected || card.activeFocus ? 2 : 1
                    border.color: card.selected || card.activeFocus ? Colors.primary : Qt.alpha(Colors.outline, 0.3)
                }
                contentItem: ColumnLayout {
                    spacing: Styling.spacing(8)
                    StyledRect {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Styling.fontSize(0) * 5.5
                        variant: "bg"
                        styleOverride: card.modelData.id
                        enableBorder: false
                        radius: Styling.radius(-5)
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: Styling.spacing(6)
                            RowLayout {
                                Layout.fillWidth: true
                                StyledText { text: Icons.layout; font.family: Icons.font; color: Colors.primary }
                                Item { Layout.fillWidth: true }
                                StyledText { text: "10:24"; font.pixelSize: Styling.fontSize(-3); font.family: Config.theme.monoFont }
                                StyledText { text: Icons.bell; font.family: Icons.font; color: Colors.primary }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Repeater {
                                    model: [Colors.primary, Colors.secondary, Colors.tertiary]
                                    delegate: StyledRect {
                                        required property color modelData
                                        variant: "transparent"
                                        color: Qt.alpha(modelData, card.modelData.id === "colorful" ? 0.42 : 0.20)
                                        radius: Styling.radius(-6)
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        implicitHeight: Styling.fontSize(0) * 1.5
                                        enableBorder: false
                                    }
                                }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText {
                            text: card.modelData.label
                            font.pixelSize: Styling.fontSize(-1)
                            font.bold: true
                            Layout.fillWidth: true
                        }
                        StyledText {
                            visible: card.selected
                            text: Icons.check
                            font.family: Icons.font
                            color: Colors.primary
                        }
                    }
                    StyledText {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        text: card.modelData.description
                        wrapMode: Text.WordWrap
                        font.pixelSize: Styling.fontSize(-2)
                        color: Colors.overSurfaceVariant
                    }
                }
            }
        }
    }
    StyledText {
        Layout.fillWidth: true
        text: "Changes save automatically. Restart Zen and reopen apps that have not updated."
        wrapMode: Text.WordWrap
        font.pixelSize: Styling.fontSize(-1)
        color: Colors.overSurfaceVariant
    }
    StyledRect {
        variant: "internalbg"
        Layout.fillWidth: true
        implicitHeight: coverage.implicitHeight + 32
        ColumnLayout {
            id: coverage
            anchors.fill: parent
            anchors.margins: 16
            spacing: Styling.spacing(8)
            StyledText { text: "App themes"; font.bold: true; color: Colors.primary }
            StyledText {
                Layout.fillWidth: true
                text: "Quickshell & Settings  ·  Zen  ·  Kitty & Fish  ·  Spotify  ·  VS Code  ·  Neovim  ·  GTK & Qt apps  ·  Vesktop  ·  Fuzzel & btop  ·  Sioyek"
                wrapMode: Text.WordWrap
            }
            StyledText {
                Layout.fillWidth: true
                text: "Each app applies the colors and transparency it supports."
                wrapMode: Text.WordWrap
                font.pixelSize: Styling.fontSize(-2)
                color: Colors.overSurfaceVariant
            }
        }
    }

}
