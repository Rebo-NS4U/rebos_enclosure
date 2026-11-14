pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.modules.components
import qs.modules.services
import qs.modules.bar.island
import qs.config
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
        contentWidth: panel.implicitWidth
        contentHeight: panel.implicitHeight

        Item {
            id: panel
            implicitWidth: Styling.spacing(440)
            implicitHeight: controls.implicitHeight + Styling.spacing(36)
            width: implicitWidth
            height: implicitHeight

            ColumnLayout {
                id: controls
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Styling.spacing(18)
                spacing: Styling.spacing(14)

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Styling.spacing(8)

                    IslandBackButton {
                        onClicked: brightnessPopup.close()
                    }
                    StyledText {
                        text: "Brightness"
                        font.pixelSize: Styling.fontSize(3)
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                }

                Separator { Layout.fillWidth: true; implicitHeight: 1 }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Styling.spacing(10)

                    StyledText {
                        text: Icons.sun
                        font.family: Icons.font
                        font.pixelSize: Styling.fontSize(4)
                        color: Colors.primary
                    }
                    StyledSlider {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 18
                        enabled: root.currentMonitor?.ready ?? false
                        stepSize: 0.01
                        value: root.value
                        onValueChanged: {
                            if (Math.abs(value - root.value) > 0.01)
                                root.adjusted(Math.max(0.05, value));
                        }
                    }
                    StyledText {
                        text: Math.round(root.value * 100) + "%"
                        font.family: Config.theme.monoFont
                        font.pixelSize: Styling.fontSize(0)
                        font.bold: true
                    }
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
