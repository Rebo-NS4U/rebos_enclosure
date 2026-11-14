pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.modules.components
import qs.modules.services
import qs.modules.theme

CircularBarMeter {
    id: root

    readonly property var currentMonitor: Brightness.getMonitorForScreen(bar.screen)

    value: currentMonitor?.brightness ?? 0.5
    icon: Icons.sun
    progressColor: BarAppearance.foregroundColor
    tooltipText: "Brightness " + Math.round(value * 100) + "%"
    clickEnabled: true
    tooltipDescription: "Scroll to adjust · Click for controls · Right-click for night light"
    onActivated: brightnessPopup.toggle()
    onSecondaryActivated: NightLightService.toggle()

    BarPopup {
        id: brightnessPopup
        anchorItem: root
        popupPadding: Styling.spacing(16)
        contentWidth: Styling.spacing(280) + popupPadding * 2
        contentHeight: controls.implicitHeight + popupPadding * 2
        ColumnLayout {
            id: controls
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: Styling.spacing(12)

            RowLayout {
                Layout.fillWidth: true
                spacing: Styling.spacing(10)

                StyledText {
                    text: Icons.sun
                    font.family: Icons.font
                    font.pixelSize: Styling.fontSize(3)
                    color: Colors.primary
                }
                StyledText {
                    text: "Brightness"
                    font.bold: true
                    Layout.fillWidth: true
                }
                StyledText {
                    text: Math.round(root.value * 100) + "%"
                    color: Colors.overSurfaceVariant
                }
            }
            StyledSlider {
                Layout.fillWidth: true
                Layout.leftMargin: Styling.spacing(8)
                Layout.rightMargin: Styling.spacing(8)
                Layout.preferredHeight: Styling.spacing(36)
                resizeParent: false
                enabled: root.currentMonitor?.ready ?? false
                stepSize: 0.01
                value: root.value
                onValueChanged: {
                    if (Math.abs(value - root.value) > 0.01)
                        root.adjusted(Math.max(0.05, value));
                }
            }
        }
    }

    onAdjusted: newValue => {
        if (Brightness.syncBrightness) {
            for (let i = 0; i < Brightness.monitors.length; i++) {
                const monitor = Brightness.monitors[i];
                if (monitor?.ready)
                    monitor.setBrightness(newValue);
            }
        } else if (currentMonitor?.ready) {
            currentMonitor.setBrightness(newValue);
        }
    }
}
