pragma ComponentBehavior: Bound

import QtQuick
import qs.modules.globals
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.modules.theme
import qs.modules.components
import qs.modules.services
import qs.modules.widgets.dashboard.controls
import qs.config

Item {
    id: root

    implicitWidth: Styling.spacing(440)
    implicitHeight: Styling.spacing(400)

    signal backRequested()

    Component.onCompleted: {
        BluetoothService.updateStatus();
        initialUpdateTimer.start();
    }

    Timer {
        id: initialUpdateTimer
        interval: 300
        repeat: false
        onTriggered: BluetoothService.updateDevices()
    }

    Component.onDestruction: {
        BluetoothService.stopDiscovery();
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Styling.spacing(18)
        spacing: Styling.spacing(14)

        // Header: Back button + Title + Actions (Settings, Rescan, Switch)
        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(8)

            // Back button
            IslandBackButton {
                onClicked: root.backRequested()
            }

            // Title
            Text {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                text: "Bluetooth"
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(3)
                font.bold: true
                color: Colors.overBackground
                elide: Text.ElideRight
            }

            // Scanning status
            Text {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                visible: BluetoothService.discovering
                text: "Scanning..."
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(-2)
                color: Styling.srItem("overprimary")
                elide: Text.ElideRight
            }

            Item { Layout.fillWidth: true }

            // Action 1: Bluetooth settings Manager (popOpen / ↗)
            ThemeButton {
                id: bluetoothSettings
                implicitWidth: Styling.spacing(36)
                implicitHeight: implicitWidth
                padding: 0
                glyph: Icons.popOpen
                Accessible.name: "Bluetooth settings"
                onClicked: { GlobalShortcuts.run("settings"); GlobalStates.settingsCurrentTab = 1; }

                StyledToolTip {
                    show: bluetoothSettings.hovered
                    tooltipText: bluetoothSettings.Accessible.name
                }
            }

            // Action 2: Rescan / Scan for devices (arrowsClockwise / 🔄)
            ThemeButton {
                id: bluetoothScan
                implicitWidth: Styling.spacing(36)
                implicitHeight: implicitWidth
                padding: 0
                glyph: Icons.arrowsClockwise
                Accessible.name: "Scan for devices"
                enabled: BluetoothService.enabled
                glyphSpinning: BluetoothService.discovering || BluetoothService.isUpdating
                onClicked: BluetoothService.startDiscovery()

                StyledToolTip {
                    show: bluetoothScan.hovered
                    tooltipText: bluetoothScan.Accessible.name
                }
            }

            // Action 3: Capsule Toggle Switch
            Item {
                id: toggleSwitch
                implicitWidth: 40
                implicitHeight: 22

                Rectangle {
                    anchors.fill: parent
                    radius: height / 2
                    color: BluetoothService.enabled ? Styling.srItem("overprimary") : Colors.surfaceBright
                    border.color: BluetoothService.enabled ? Styling.srItem("overprimary") : Colors.outline
                    border.width: Config.controlBorderWidth

                    Behavior on color {
                        enabled: Config.animDuration > 0
                        ColorAnimation { duration: Motion.feedback }
                    }

                    Rectangle {
                        x: BluetoothService.enabled ? parent.width - width - 2 : 2
                        y: 2
                        width: parent.height - 4
                        height: width
                        radius: width / 2
                        color: BluetoothService.enabled ? Colors.background : Colors.overSurfaceVariant

                        Behavior on x {
                            enabled: Config.animDuration > 0
                            NumberAnimation {
                                duration: Motion.feedback
                                easing.type: Easing.OutCubic
                            }
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        const newState = !BluetoothService.enabled;
                        BluetoothService.setEnabled(newState, newState);
                    }
                }
            }
        }

        Separator { Layout.fillWidth: true; implicitHeight: 1 }

        BluetoothPairingPrompt {
            Layout.fillWidth: true
        }

        // Bluetooth device list
        StyledText {
            Layout.fillWidth: true
            visible: BluetoothService.lastError.length > 0
            text: BluetoothService.lastError
            color: Colors.error
            wrapMode: Text.Wrap
            maximumLineCount: 3
            elide: Text.ElideRight
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: deviceList
                anchors.fill: parent
                clip: true
                spacing: Styling.spacing(6)
                model: BluetoothService.deviceModel

                delegate: Item {
                    id: delegateRoot
                    required property var device
                    width: deviceList.width
                    height: deviceItem.implicitHeight

                    BluetoothDeviceItem {
                        id: deviceItem
                        width: parent.width
                        baseVariant: "internalbg"
                        device: delegateRoot.device
                    }
                }
            }

            // Empty state: no devices found or disabled
            Text {
                anchors.centerIn: parent
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                visible: deviceList.count === 0 && !BluetoothService.discovering
                text: BluetoothService.enabled ? "No devices found" : "Bluetooth is disabled"
                font.family: Config.theme.font
                font.pixelSize: Config.theme.fontSize
                color: Colors.overSurfaceVariant
            }

            // Scanning indicator when list is empty
            RowLayout {
                anchors.centerIn: parent
                visible: deviceList.count === 0 && BluetoothService.discovering
                spacing: Styling.spacing(8)

                Text {
                    text: Icons.arrowsClockwise
                    font.family: Icons.font
                    font.pixelSize: Styling.fontSize(2)
                    color: Styling.srItem("overprimary")

                    RotationAnimation on rotation {
                        running: BluetoothService.discovering
                        from: 0
                        to: 360
                        duration: 1000
                        loops: Animation.Infinite
                    }
                }

                Text {
                    text: "Scanning for devices..."
                    font.family: Config.theme.font
                    font.pixelSize: Config.theme.fontSize
                    color: Colors.overSurfaceVariant
                }
            }
        }
    }
}
