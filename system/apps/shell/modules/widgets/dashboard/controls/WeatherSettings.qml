pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.theme
import qs.modules.components
import qs.config

SettingsGroup {
    title: "Weather widget"
    property string settingsSection: "weather"
    description: "Choose a location and temperature units."
    Layout.fillWidth: true



    // Location
    RowLayout {
        Layout.fillWidth: true
        spacing: Styling.spacing(8)

        StyledText {
            renderType: Text.NativeRendering
            font.hintingPreference: Font.PreferFullHinting
            text: "Location"
            font.family: Config.theme.font
            font.pixelSize: Styling.fontSize(0)
            color: Colors.overBackground
            Layout.preferredWidth: 100
        }

        StyledRect {
            variant: "common"
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            radius: Styling.radius(-2)

            TextInput {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                id: locationInput
                anchors.fill: parent
                anchors.margins: 8
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(0)
                color: Colors.overBackground
                selectByMouse: true
                clip: true
                verticalAlignment: TextInput.AlignVCenter

                readonly property string configValue: Config.weather.location

                onConfigValueChanged: {
                    if (text !== configValue) {
                        text = configValue;
                    }
                }

                Component.onCompleted: text = configValue

                onEditingFinished: {
                    if (text !== Config.weather.location) {
                        Config.weather.location = text.trim();
                    }
                }

                StyledText {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: !locationInput.text && !locationInput.activeFocus
                    text: "e.g. Buenos Aires, Tokyo..."
                    font: locationInput.font
                    color: Colors.overSurfaceVariant
                }
            }
        }
    }

    // Unit selector
    RowLayout {
        Layout.fillWidth: true
        spacing: Styling.spacing(8)

        StyledText {
            renderType: Text.NativeRendering
            font.hintingPreference: Font.PreferFullHinting
            text: "Temperature unit"
            font.family: Config.theme.font
            font.pixelSize: Styling.fontSize(0)
            color: Colors.overBackground
            Layout.preferredWidth: 100
        }

        Row {
            spacing: Styling.spacing(8)

            Repeater {
                model: [
                    {
                        id: "C",
                        label: "Celsius"
                    },
                    {
                        id: "F",
                        label: "Fahrenheit"
                    }
                ]

                delegate: StyledRect {
                    id: unitButton
                    required property var modelData
                    required property int index

                    property bool isSelected: Config.weather.unit === modelData.id
                    property bool isHovered: false

                    variant: isSelected ? "primary" : (isHovered ? "focus" : "common")
                    width: unitLabel.width + 24
                    height: 36
                    radius: Styling.radius(-2)

                    StyledText {
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        id: unitLabel
                        anchors.centerIn: parent
                        text: unitButton.modelData.label
                        font.family: Config.theme.font
                        font.pixelSize: Styling.fontSize(0)
                        font.weight: unitButton.isSelected ? Font.Bold : Font.Normal
                        color: unitButton.item
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onEntered: unitButton.isHovered = true
                        onExited: unitButton.isHovered = false
                        onClicked: Config.weather.unit = unitButton.modelData.id
                    }
                }
            }
        }
    }
}
