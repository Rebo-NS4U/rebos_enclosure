pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.modules.theme
import qs.modules.services

RowLayout {
    spacing: Styling.spacing(6)
    Repeater {
        model: ["keyboard", "touchscreen"]
        StyledRect {
            id: button
            required property string modelData
            readonly property bool switchedOn: InputService.disabled !== modelData
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            implicitHeight: 30
            radius: Styling.radius(2)
            variant: mouse.containsMouse || activeFocus ? "focus" : "internalbg"
            activeFocusOnTab: true
            enabled: (modelData === "keyboard" ? InputService.keyboardAvailable : InputService.touchscreenAvailable)
                && (InputService.disabled === "" || !switchedOn)
            opacity: enabled ? 1 : 0.45
            Keys.onSpacePressed: InputService.toggle(modelData)
            Keys.onReturnPressed: InputService.toggle(modelData)
            RowLayout {
                anchors.centerIn: parent
                spacing: Styling.spacing(6)
                StyledText {
                    text: button.modelData === "keyboard" ? Icons.keyboard : Icons.hand
                    font.family: Icons.font
                    color: button.switchedOn ? Colors.overSurfaceVariant : Colors.primary
                }
                StyledText {
                    text: (button.modelData === "keyboard" ? "Keyboard" : "Touch") + (button.switchedOn ? "" : " off")
                    font.pixelSize: Styling.fontSize(-2)
                    color: button.switchedOn ? Colors.overSurfaceVariant : Colors.primary
                }
            }
            MouseArea {
                id: mouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: InputService.toggle(button.modelData)
            }
            StyledToolTip {
                show: mouse.containsMouse || button.activeFocus
                tooltipText: InputService.tooltip(button.modelData)
            }
        }
    }
}
