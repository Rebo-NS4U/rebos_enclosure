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
    description: ""
    property string settingsSection: "style"

    component FinishPicker: ColumnLayout {
        id: picker
        required property string label
        required property string setting
        required property var options
        Layout.fillWidth: true

        StyledText { text: picker.label }
        Flow {
            Layout.fillWidth: true
            spacing: Styling.spacing(6)
            Repeater {
                model: picker.options
                delegate: SettingsButton {
                    required property var modelData
                    objectName: picker.setting + "-" + modelData.value
                    text: modelData.label
                    Accessible.name: picker.label + ", " + text
                    checked: Config.theme[picker.setting] === modelData.value
                    onClicked: Config.theme[picker.setting] = modelData.value
                }
            }
        }
    }

    FinishPicker {
        label: "Button finish"
        setting: "buttonFinish"
        options: [{value: "default", label: "Theme default"}, {value: "inset", label: "Inset rim"}, {value: "underline", label: "Underline"}]
    }

    FinishPicker {
        label: "Background finish"
        setting: "backgroundFinish"
        options: [{value: "default", label: "Theme default"}, {value: "wash", label: "Accent wash"}, {value: "two-tone", label: "Two-tone"}]
    }

    GridLayout {
        objectName: "theme-preview-grid"
        uniformCellWidths: true
        columns: width >= 1440 ? 6 : width >= 640 ? 3 : width >= 380 ? 2 : 1
        Layout.fillWidth: true
        columnSpacing: Styling.spacing(10)
        rowSpacing: Styling.spacing(10)
        Repeater {
            model: ShellStyles.styles
            delegate: Button {
                id: card
                required property var modelData
                objectName: "shell-style-" + modelData.id
                StyledToolTip { show: card.hovered; tooltipText: card.modelData.description }
                readonly property bool selected: Styling.shellStyle === modelData.id
                readonly property var previewPalette: ShellStyles.themePalette(modelData.id)
                readonly property var sample: Styling.styleConfig(modelData.id, "bg")
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                implicitHeight: Math.max(104, implicitContentHeight + padding * 2)
                padding: 10
                onClicked: {
                    Config.theme.shellStyle = modelData.id;
                    if (["frosted", "colorful", "glass-vault", "radar-station", "frosted-ceramic", "canopy", "orbital", "metropolis", "clear-glass"].indexOf(modelData.id) !== -1) {
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
                        Layout.preferredHeight: 42
                        variant: "bg"
                        materialPreview: true
                        styleOverride: card.modelData.id
                        enableBorder: false
                        radius: Styling.radius(-5)
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            Rectangle { implicitWidth: 26; implicitHeight: 5; radius: 2; color: card.previewPalette ? card.previewPalette.primary : Colors.primary; opacity: 0.7 }
                            Item { Layout.fillWidth: true }
                            StyledText { text: "10:24"; color: card.sample.itemColor; font.pixelSize: Styling.fontSize(-3); font.family: Config.theme.monoFont }
                            Repeater {
                                model: card.previewPalette ? [card.previewPalette.primary, card.previewPalette.secondary, card.previewPalette.tertiary] : [Colors.primary, Colors.secondary, Colors.tertiary]
                                delegate: Rectangle {
                                    required property color modelData
                                    implicitWidth: 7; implicitHeight: 7; radius: 3
                                    color: modelData
                                }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText {
                            font.family: ShellStyles.fontForStyle(card.modelData.id, Config.theme.font)
                            text: card.modelData.label
                            wrapMode: Text.WordWrap
                            Layout.minimumWidth: 0
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

                }
            }
        }
    }
}
