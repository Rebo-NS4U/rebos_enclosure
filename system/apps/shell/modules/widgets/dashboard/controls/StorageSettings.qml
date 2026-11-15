pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.theme
import qs.modules.components
import qs.config

SettingsGroup {
    title: "Storage monitor"
    property string settingsSection: "storage"
    description: "Choose the disks shown in the system monitor."
    Layout.fillWidth: true



    StyledText {
        renderType: Text.NativeRendering
        font.hintingPreference: Font.PreferFullHinting
        text: "Choose disks for the system monitor."
        font.family: Config.theme.font
        font.pixelSize: Styling.fontSize(-2)
        color: Colors.overSurfaceVariant
        opacity: 0.7
    }

    // Disks list
    ColumnLayout {
        Layout.fillWidth: true
        spacing: Styling.spacing(4)

        Repeater {
            id: disksRepeater
            model: Config.system.disks

            delegate: RowLayout {
                id: diskRow
                required property string modelData
                required property int index

                Layout.fillWidth: true
                spacing: Styling.spacing(8)

                StyledRect {
                    variant: "common"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    radius: Styling.radius(-2)

                    TextInput {
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        id: diskInput
                        anchors.fill: parent
                        anchors.margins: 8
                        font.family: Config.theme.monoFont
                        font.pixelSize: Styling.monoFontSize(0)
                        color: Colors.overBackground
                        selectByMouse: true
                        clip: true
                        verticalAlignment: TextInput.AlignVCenter
                        text: diskRow.modelData

                        onEditingFinished: {
                            if (text.trim() !== diskRow.modelData) {
                                let newDisks = Config.system.disks.slice();
                                newDisks[diskRow.index] = text.trim();
                                Config.system.disks = newDisks;
                            }
                        }

                        StyledText {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: !diskInput.text && !diskInput.activeFocus
                            text: "e.g. /, /home..."
                            font: diskInput.font
                            color: Colors.overSurfaceVariant
                        }
                    }
                }

                // Remove button
                StyledRect {
                    id: removeDiskButton
                    variant: removeDiskArea.containsMouse ? "focus" : "common"
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    radius: Styling.radius(-2)
                    visible: disksRepeater.count > 1

                    StyledText {
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        anchors.centerIn: parent
                        text: Icons.trash
                        font.family: Icons.font
                        font.pixelSize: Styling.fontSize(0)
                        color: Colors.error
                    }

                    MouseArea {
                        id: removeDiskArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            let newDisks = Config.system.disks.slice();
                            newDisks.splice(diskRow.index, 1);
                            Config.system.disks = newDisks;
                        }
                    }

                    StyledToolTip {
                        show: removeDiskArea.containsMouse
                        tooltipText: "Remove disk"
                    }
                }
            }
        }

        // Add disk button
        StyledRect {
            id: addDiskButton
            variant: addDiskArea.containsMouse ? "primaryfocus" : "primary"
            Layout.preferredWidth: addDiskContent.width + 24
            Layout.preferredHeight: 36
            radius: Styling.radius(-2)

            Row {
                id: addDiskContent
                anchors.centerIn: parent
                spacing: Styling.spacing(6)

                StyledText {
                    renderType: Text.NativeRendering
                    font.hintingPreference: Font.PreferFullHinting
                    text: Icons.plus
                    font.family: Icons.font
                    font.pixelSize: Styling.fontSize(0)
                    color: addDiskButton.item
                    anchors.verticalCenter: parent.verticalCenter
                }

                StyledText {
                    renderType: Text.NativeRendering
                    font.hintingPreference: Font.PreferFullHinting
                    text: "Add Disk"
                    font.family: Config.theme.font
                    font.pixelSize: Styling.fontSize(0)
                    color: addDiskButton.item
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            MouseArea {
                id: addDiskArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    let newDisks = Config.system.disks.slice();
                    newDisks.push("/");
                    Config.system.disks = newDisks;
                }
            }
        }
    }
}
