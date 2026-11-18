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
        NetworkService.rescanWifi();
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Styling.spacing(18)
        spacing: Styling.spacing(14)

        // Header: Back button + Title + Actions (Globe, Settings, Rescan, Switch)
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
                text: "Wi-Fi"
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(3)
                font.bold: true
                color: Colors.overBackground
                elide: Text.ElideRight
            }

            // Status label (connecting, limited, or VPN)
            Text {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                visible: NetworkService.wifiConnecting || NetworkService.wifiStatus === "limited" || NetworkService.vpnConnected
                text: NetworkService.wifiConnecting ? "Connecting..." : (NetworkService.wifiStatus === "limited" ? "Limited" : (NetworkService.vpnConnected ? ("VPN: " + (NetworkService.vpnName || "Active")) : ""))
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(-2)
                color: NetworkService.wifiStatus === "limited" ? Colors.warning : Styling.srItem("overprimary")
                elide: Text.ElideRight
            }

            Item { Layout.fillWidth: true }

            // Action 1: Captive Portal (Globe)
            ThemeButton {
                id: portalButton
                implicitWidth: Styling.spacing(36)
                implicitHeight: implicitWidth
                padding: 0
                glyph: Icons.globe
                Accessible.name: "Open captive portal"
                enabled: NetworkService.wifiStatus === "limited"
                onClicked: NetworkService.openPublicWifiPortal()

                StyledToolTip {
                    show: portalButton.hovered
                    tooltipText: portalButton.Accessible.name
                }
            }

            // Action 2: Network Settings (popOpen / ↗)
            ThemeButton {
                id: networkSettings
                implicitWidth: Styling.spacing(36)
                implicitHeight: implicitWidth
                padding: 0
                glyph: Icons.popOpen
                Accessible.name: "Network settings"
                onClicked: { GlobalShortcuts.run("settings"); GlobalStates.settingsCurrentTab = 0; }

                StyledToolTip {
                    show: networkSettings.hovered
                    tooltipText: networkSettings.Accessible.name
                }
            }

            // Action 3: Rescan networks (arrowsClockwise / 🔄)
            ThemeButton {
                id: networkScan
                implicitWidth: Styling.spacing(36)
                implicitHeight: implicitWidth
                padding: 0
                glyph: Icons.arrowsClockwise
                Accessible.name: "Rescan networks"
                enabled: NetworkService.wifiEnabled && !glyphSpinning
                glyphSpinning: NetworkService.wifiScanning || NetworkService.isUpdating
                onClicked: NetworkService.rescanWifi()

                StyledToolTip {
                    show: networkScan.hovered
                    tooltipText: networkScan.Accessible.name
                }
            }

            // Action 4: Capsule Toggle Switch
            Item {
                id: toggleSwitch
                enabled: !NetworkService.isUpdating
                implicitWidth: 40
                implicitHeight: 22

                Rectangle {
                    anchors.fill: parent
                    radius: height / 2
                    color: NetworkService.wifiEnabled ? Styling.srItem("overprimary") : Colors.surfaceBright
                    border.color: NetworkService.wifiEnabled ? Styling.srItem("overprimary") : Colors.outline
                    border.width: 1

                    Behavior on color {
                        enabled: Config.animDuration > 0
                        ColorAnimation { duration: Motion.feedback }
                    }

                    Rectangle {
                        x: NetworkService.wifiEnabled ? parent.width - width - 2 : 2
                        y: 2
                        width: parent.height - 4
                        height: width
                        radius: width / 2
                        color: NetworkService.wifiEnabled ? Colors.background : Colors.overSurfaceVariant

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
                        const next = !NetworkService.wifiEnabled;
                        NetworkService.enableWifi(next);
                    }
                }
            }
        }

        Separator { Layout.fillWidth: true; implicitHeight: 1 }

        StyledText {
            Layout.fillWidth: true
            visible: NetworkService.lastError.length > 0
            text: NetworkService.lastError
            color: Colors.error
            wrapMode: Text.Wrap
            maximumLineCount: 3
            elide: Text.ElideRight
        }

        // Wi-Fi network list
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: wifiList
                anchors.fill: parent
                clip: true
                spacing: Styling.spacing(6)
                model: NetworkService.friendlyWifiNetworks

                delegate: Item {
                    id: delegateRoot
                    required property var modelData
                    width: wifiList.width
                    height: networkItem.implicitHeight

                    WifiNetworkItem {
                        id: networkItem
                        width: parent.width
                        baseVariant: "internalbg"
                        network: delegateRoot.modelData
                    }
                }
            }

            // Empty state: no networks found or disabled
            Text {
                anchors.centerIn: parent
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                visible: wifiList.count === 0 && !NetworkService.wifiScanning
                text: NetworkService.wifiEnabled ? "No networks found" : "Wi-Fi is disabled"
                font.family: Config.theme.font
                font.pixelSize: Config.theme.fontSize
                color: Colors.overSurfaceVariant
            }

            // Scanning indicator when list is empty
            RowLayout {
                anchors.centerIn: parent
                visible: wifiList.count === 0 && NetworkService.wifiScanning
                spacing: Styling.spacing(8)

                Text {
                    text: Icons.arrowsClockwise
                    font.family: Icons.font
                    font.pixelSize: Styling.fontSize(2)
                    color: Styling.srItem("overprimary")

                    RotationAnimation on rotation {
                        running: NetworkService.wifiScanning
                        from: 0
                        to: 360
                        duration: 1000
                        loops: Animation.Infinite
                    }
                }

                Text {
                    text: "Scanning for networks..."
                    font.family: Config.theme.font
                    font.pixelSize: Config.theme.fontSize
                    color: Colors.overSurfaceVariant
                }
            }
        }
    }
}
