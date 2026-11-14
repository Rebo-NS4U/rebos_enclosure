pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Services.Pipewire
import qs.modules.theme
import qs.modules.components
import qs.modules.services
import qs.config

Item {
    id: root

    implicitWidth: Styling.spacing(440)
    implicitHeight: Math.min(480, mainColumn.implicitHeight + Styling.spacing(36))

    signal backRequested()

    readonly property real volume: Audio.sink?.audio?.volume ?? 0.0
    readonly property bool isMuted: Audio.sink?.audio?.muted ?? false
    readonly property string activeSinkId: Audio.sink?.id ? String(Audio.sink.id) : ""

    readonly property var outputDevices: {
        const nodes = Pipewire.nodes.values;
        if (!nodes)
            return [];
        return nodes.filter(node => node && node.isSink && !node.isStream && node.audio);
    }

    readonly property var appNodes: {
        const nodes = Pipewire.nodes.values;
        if (!nodes)
            return [];
        return nodes.filter(node => node && node.isSink && node.isStream && node.audio);
    }

    ColumnLayout {
        id: mainColumn
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Styling.spacing(18)
        spacing: Styling.spacing(14)

        // Header: Back button + Title + Audio Format Badge
        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(8)

            IslandBackButton {
                onClicked: root.backRequested()
            }

            Text {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                text: "Sound"
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(3)
                font.bold: true
                color: Colors.overBackground
            }

            Item { Layout.fillWidth: true }

            // Audio Format / Bitrate Badge (Sample rate & bit depth)
            StyledRect {
                visible: AudioFormat.connected
                implicitHeight: 26
                implicitWidth: fmtRow.implicitWidth + 16
                radius: Styling.radius(0)
                variant: "internalbg"

                RowLayout {
                    id: fmtRow
                    anchors.centerIn: parent
                    spacing: Styling.spacing(6)

                    Text {
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        text: AudioFormat.kindIcon
                        font.family: Icons.font
                        font.pixelSize: Styling.fontSize(-1)
                        color: Colors.primary
                    }

                    Text {
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        text: AudioFormat.formatSummary
                        font.family: Config.theme.monoFont
                        font.pixelSize: Styling.fontSize(-2)
                        font.bold: true
                        color: Colors.overBackground
                    }
                }
            }
        }

        Separator { Layout.fillWidth: true; implicitHeight: 1 }

        // Master Volume Slider row
        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(10)

            Item {
                implicitWidth: 22
                implicitHeight: 22
                Layout.alignment: Qt.AlignVCenter

                Text {
                    anchors.centerIn: parent
                    renderType: Text.NativeRendering
                    font.hintingPreference: Font.PreferFullHinting
                    text: root.isMuted ? Icons.speakerSlash : (root.volume > 0.5 ? Icons.speakerHigh : (root.volume > 0 ? Icons.speakerLow : Icons.speakerSlash))
                    font.family: Icons.font
                    font.pixelSize: Styling.fontSize(4)
                    color: root.isMuted ? Colors.red : Colors.overBackground
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Audio.toggleMute()
                }
            }

            // Slider track
            StyledSlider {
                id: volSlider
                Layout.fillWidth: true
                Layout.preferredHeight: 18
                value: root.volume
                progressColor: root.isMuted ? Colors.outlineVariant : Colors.primary
                onValueChanged: {
                    if (Audio.sink?.audio && Math.abs(value - root.volume) > 0.01) {
                        Audio.sink.audio.volume = value;
                    }
                }
            }

            Text {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                text: Math.round(root.volume * 100) + "%"
                font.family: Config.theme.monoFont
                font.pixelSize: Styling.fontSize(0)
                font.bold: true
                color: Colors.overBackground
            }
        }

        // Scrollable content area for devices and app mixer
        Item {
            Layout.fillWidth: true
            implicitHeight: Math.min(320, scrollContent.implicitHeight)

            Flickable {
                anchors.fill: parent
                contentHeight: scrollContent.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                ColumnLayout {
                    id: scrollContent
                    width: parent.width
                    spacing: Styling.spacing(8)

                    // Section 1: Output Devices
                    Text {
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        text: "Output device"
                        font.family: Config.theme.monoFont
                        font.pixelSize: Styling.fontSize(-2)
                        font.bold: true
                        color: Colors.overSurfaceVariant
                        Layout.topMargin: 4
                    }

                    Repeater {
                        model: root.outputDevices

                        delegate: Item {
                            id: delegateRoot
                            required property PwNode modelData

                            PwObjectTracker {
                                objects: [delegateRoot.modelData]
                            }

                            Layout.fillWidth: true
                            implicitHeight: Styling.spacing(44)

                            readonly property bool isCurrent: delegateRoot.modelData === Audio.sink || String(delegateRoot.modelData.id) === root.activeSinkId

                            StyledRect {
                                anchors.fill: parent
                                radius: Styling.radius(2)
                                variant: delegateRoot.isCurrent || devMouse.containsMouse ? "focus" : "common"
                                enableBorder: true
                                border.color: delegateRoot.isCurrent ? Colors.primary : Qt.alpha(Colors.outline, 0.2)

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    spacing: Styling.spacing(8)

                                    Text {
                                        renderType: Text.NativeRendering
                                        font.hintingPreference: Font.PreferFullHinting
                                        text: Icons.speakerHigh
                                        font.family: Icons.font
                                        font.pixelSize: Styling.fontSize(2)
                                        color: Colors.overBackground
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        renderType: Text.NativeRendering
                                        font.hintingPreference: Font.PreferFullHinting
                                        text: Audio.friendlyDeviceName(delegateRoot.modelData)
                                        font.family: Config.theme.font
                                        font.pixelSize: Styling.fontSize(0)
                                        font.bold: delegateRoot.isCurrent
                                        color: Colors.overBackground
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        visible: delegateRoot.isCurrent
                                        renderType: Text.NativeRendering
                                        font.hintingPreference: Font.PreferFullHinting
                                        text: Icons.check
                                        font.family: Icons.font
                                        font.pixelSize: Styling.fontSize(2)
                                        color: Colors.primary
                                    }
                                }

                                MouseArea {
                                    id: devMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        Audio.setDefaultSink(delegateRoot.modelData);
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        visible: root.outputDevices.length === 0
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        text: "No output devices found"
                        font.family: Config.theme.font
                        font.pixelSize: Styling.fontSize(-1)
                        color: Colors.overSurfaceVariant
                        opacity: 0.6
                        Layout.topMargin: 2
                        Layout.bottomMargin: 2
                    }

                    // Section 2: Application Audio Streams
                    Text {
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        text: "Applications"
                        font.family: Config.theme.monoFont
                        font.pixelSize: Styling.fontSize(-2)
                        font.bold: true
                        color: Colors.overSurfaceVariant
                        Layout.topMargin: 8
                    }

                    Repeater {
                        model: root.appNodes

                        delegate: Item {
                            id: appDelegate
                            required property PwNode modelData

                            PwObjectTracker {
                                objects: [appDelegate.modelData]
                            }

                            Layout.fillWidth: true
                            implicitHeight: 60

                            readonly property bool isAppMuted: appDelegate.modelData?.audio?.muted ?? false
                            readonly property real appVolume: appDelegate.modelData?.audio?.volume ?? 0.0

                            StyledRect {
                                anchors.fill: parent
                                radius: Styling.radius(2)
                                variant: "internalbg"

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 14
                                    anchors.rightMargin: 14
                                    anchors.topMargin: 9
                                    anchors.bottomMargin: 10
                                    spacing: Styling.spacing(6)

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: Styling.spacing(6)

                                        Item {
                                            implicitWidth: 16
                                            implicitHeight: 16
                                            Layout.alignment: Qt.AlignVCenter

                                            Text {
                                                anchors.centerIn: parent
                                                renderType: Text.NativeRendering
                                                font.hintingPreference: Font.PreferFullHinting
                                                text: appDelegate.isAppMuted ? Icons.speakerSlash : (appDelegate.appVolume > 0.5 ? Icons.speakerHigh : (appDelegate.appVolume > 0 ? Icons.speakerLow : Icons.speakerSlash))
                                                font.family: Icons.font
                                                font.pixelSize: Styling.fontSize(-1)
                                                color: appDelegate.isAppMuted ? Colors.red : Colors.overBackground
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    if (appDelegate.modelData?.audio) {
                                                        appDelegate.modelData.audio.muted = !appDelegate.modelData.audio.muted;
                                                    }
                                                }
                                            }
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            renderType: Text.NativeRendering
                                            font.hintingPreference: Font.PreferFullHinting
                                            text: Audio.appNodeDisplayName(appDelegate.modelData)
                                            font.family: Config.theme.font
                                            font.pixelSize: Styling.fontSize(-1)
                                            font.bold: true
                                            color: Colors.overBackground
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            renderType: Text.NativeRendering
                                            font.hintingPreference: Font.PreferFullHinting
                                            text: Math.round(appDelegate.appVolume * 100) + "%"
                                            font.family: Config.theme.monoFont
                                            font.pixelSize: Styling.fontSize(-2)
                                            color: Colors.overSurfaceVariant
                                        }
                                    }

                                    StyledSlider {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 16
                                        Layout.leftMargin: 2
                                        Layout.rightMargin: 2
                                        value: appDelegate.appVolume
                                        progressColor: appDelegate.isAppMuted ? Colors.outlineVariant : Colors.primary
                                        onValueChanged: {
                                            if (appDelegate.modelData?.audio && Math.abs(value - appDelegate.appVolume) > 0.01) {
                                                Audio.setNodeVolume(appDelegate.modelData, value);
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        visible: root.appNodes.length === 0
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        text: "No applications playing audio"
                        font.family: Config.theme.font
                        font.pixelSize: Styling.fontSize(-1)
                        color: Colors.overSurfaceVariant
                        opacity: 0.6
                        Layout.topMargin: 2
                        Layout.bottomMargin: 4
                    }
                }
            }
        }
    }
}
