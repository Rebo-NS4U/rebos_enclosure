import QtQuick
import QtQuick.Layouts
import qs.modules.theme
import qs.modules.components
import qs.modules.services
import qs.modules.widgets.dashboard.widgets

RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Styling.spacing(4)
            Repeater {
                model: ["keyboard", "touchscreen"]
                ColumnLayout {
                    id: inputTile
                    required property string modelData
                    spacing: Styling.spacing(2)
                    ControlButton {
                    readonly property string modelData: inputTile.modelData
                    activeFocusOnTab: true
                    border.width: activeFocus ? 2 : 0
                    border.color: item
                    Keys.onSpacePressed: InputService.toggle(modelData)
                    Keys.onReturnPressed: InputService.toggle(modelData)
                    Layout.preferredWidth: 48
                    Layout.preferredHeight: 48
                    iconName: modelData === "keyboard" ? Icons.keyboard : Icons.hand
                    isActive: InputService.disabled !== modelData
                    enabled: (modelData === "keyboard" ? InputService.keyboardAvailable : InputService.touchscreenAvailable)
                        && (InputService.disabled === "" || InputService.disabled === modelData)
                    opacity: enabled ? 1 : 0.4
                    tooltipText: InputService.tooltip(modelData)
                    onClicked: InputService.toggle(modelData)
                    }
                    StyledText {
                        Layout.alignment: Qt.AlignHCenter
                        text: inputTile.modelData === "keyboard" ? "Keyboard" : "Touchscreen"
                        font.pixelSize: Styling.fontSize(-2)
                    }
                }
            }
            StyledText {
                text: InputService.error || (InputService.disabled !== ""
                    ? "Auto restore: " + InputService.remaining + "s" : "Input safety: one stays on")
                Layout.maximumWidth: 220
                wrapMode: Text.WordWrap
            }
        }

