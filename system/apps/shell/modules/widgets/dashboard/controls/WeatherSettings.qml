pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.theme
import qs.modules.components
import qs.config
import qs.modules.globals

SettingsGroup {
    id: root
    title: "Weather"
    property string settingsSection: "weather"
    readonly property var wallpaperManager: GlobalStates.wallpaperManager
    readonly property bool orbitEnabled: wallpaperManager?.orbitSelected ?? false
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

    ColumnLayout {
        Layout.fillWidth: true
        spacing: Styling.spacing(8)

        StyledText {
            objectName: "weather-unit-label"
            text: "Temperature units"
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(8)
            Repeater {
                model: [
                    { id: "C", label: "Celsius (°C)" },
                    { id: "F", label: "Fahrenheit (°F)" }
                ]
                delegate: SettingsButton {
                    required property var modelData
                    objectName: "weather-unit-" + modelData.id
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: modelData.label
                    highlighted: Config.weather.unit === modelData.id
                    Accessible.name: modelData.label
                    onClicked: Config.weather.unit = modelData.id
                }
            }
        }
    }
    SettingsToggleRow {
        objectName: "weather-live-wallpaper"
        label: "Orbit live wallpaper"
        checked: root.orbitEnabled
        enabled: !!root.wallpaperManager
        onToggled: checked => root.wallpaperManager?.setOrbitEnabled(checked)
    }

    OrbitWallpaperSettings {
        visible: root.orbitEnabled
    }

    WallpaperSettings {
        objectName: "weather-regular-wallpaper"
        visible: !root.orbitEnabled
    }
}
