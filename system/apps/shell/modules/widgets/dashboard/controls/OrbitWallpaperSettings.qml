pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Dialogs
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.modules.components
import qs.modules.theme

SettingsGroup {
    id: root
    objectName: "orbit-wallpaper-settings"
    title: "Orbit Wallpaper"
    property string settingsAnchor: "orbit-wallpaper"
    property var saved: null
    property var inFlight: ({})
    property var pending: ({})
    property bool checkedConnection: false
    readonly property var defaults: ({
        paper: "#000000", ink: "#f2f2f2", accent: "#d71921",
        orbitSpeed: 1, starCount: 560, showLabels: true
    })
    readonly property var appearance: Object.assign({}, defaults, saved, inFlight, pending)

    function apply(patch): void {
        pending = Object.assign({}, pending, patch);
        exchange();
    }

    function exchange(): void {
        if (client.running)
            return;
        inFlight = pending;
        pending = {};
        const path = Quickshell.env("HOME") + "/.config/enclosure/orbit-wallpaper";
        client.command = ["qs", "ipc", "-p", path, "call", "settings", "appearance", JSON.stringify(inFlight)];
        client.running = true;
    }

    onVisibleChanged: if (visible) exchange()
    Component.onCompleted: if (visible) exchange()

    Timer {
        interval: 2500
        running: root.visible
        repeat: true
        onTriggered: root.exchange()
    }

    Process {
        id: client
        stdout: StdioCollector { id: response }
        onExited: code => {
            try {
                root.saved = code === 0 ? JSON.parse(response.text) : null;
            } catch (error) {
                root.saved = null;
            }
            root.checkedConnection = true;
            root.inFlight = {};
            if (Object.keys(root.pending).length)
                root.exchange();
        }
    }

    ColorDialog {
        id: picker
        property string setting
        onAccepted: root.apply({[setting]: String(selectedColor)})
    }

    StyledText {
        visible: root.checkedConnection && !root.saved
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        text: "The Orbit live wallpaper service is unavailable."
    }

    ColumnLayout {
        visible: !!root.saved
        Layout.fillWidth: true
        spacing: Styling.spacing(12)

        RowLayout {
            Layout.fillWidth: true
            StyledText { text: "Palette"; Layout.fillWidth: true }
            SettingsButton {
                text: "Classic"
                onClicked: root.apply({paper: root.defaults.paper, ink: root.defaults.ink, accent: root.defaults.accent})
            }
            SettingsButton {
                objectName: "orbit-nebula"
                text: "Nebula"
                onClicked: root.apply({paper: "#140d25", ink: "#e8ceff", accent: "#ff69a5"})
            }
            SettingsButton {
                text: "Aurora"
                onClicked: root.apply({paper: "#081d22", ink: "#baf9de", accent: "#57c4ff"})
            }
        }

        Repeater {
            model: [
                {label: "Background", key: "paper"},
                {label: "Stars, planets and rings", key: "ink"},
                {label: "Gravity well core and alerts", key: "accent"}
            ]
            RowLayout {
                id: row
                required property var modelData
                readonly property string hex: root.appearance[modelData.key]
                Layout.fillWidth: true
                StyledText { text: row.modelData.label; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Rectangle {
                    implicitWidth: 24
                    implicitHeight: 24
                    radius: Styling.radius(-4)
                    color: row.hex
                    border.color: Colors.outline
                }
                SettingsButton {
                    text: row.hex.toUpperCase()
                    Accessible.name: "Choose " + row.modelData.label + " color"
                    onClicked: {
                        picker.setting = row.modelData.key;
                        picker.title = row.modelData.label;
                        picker.selectedColor = row.hex;
                        picker.open();
                    }
                }
            }
        }

        Repeater {
            model: [
                {label: "Orbit speed", key: "orbitSpeed", max: 3, step: 0.25},
                {label: "Star density", key: "starCount", max: 1000, step: 20}
            ]
            RowLayout {
                id: sliderRow
                required property var modelData
                readonly property real amount: root.appearance[modelData.key]
                Layout.fillWidth: true
                StyledText { text: sliderRow.modelData.label; Layout.minimumWidth: 110 }
                StyledSlider {
                    Accessible.name: sliderRow.modelData.label
                    value: sliderRow.amount / sliderRow.modelData.max
                    stepSize: sliderRow.modelData.step / sliderRow.modelData.max
                    snapMode: "always"
                    scroll: false
                    tooltip: false
                    updateOnRelease: true
                    onValueChanged: {
                        const next = Math.round(value / stepSize) * sliderRow.modelData.step;
                        if (root.saved && next !== sliderRow.amount)
                            root.apply({[sliderRow.modelData.key]: next});
                    }
                }
                StyledText {
                    Layout.minimumWidth: 70
                    horizontalAlignment: Text.AlignRight
                    text: sliderRow.modelData.key === "starCount" ? sliderRow.amount.toFixed(0)
                        : sliderRow.amount === 0 ? "Paused" : sliderRow.amount.toFixed(2) + "×"
                }
            }
        }

        SettingsToggleRow {
            label: "Show window titles on hover"
            checked: root.appearance.showLabels
            onToggled: checked => root.apply({showLabels: checked})
        }

        SettingsButton {
            objectName: "orbit-restore-defaults"
            text: "Restore defaults"
            onClicked: root.apply(root.defaults)
        }
    }
}
