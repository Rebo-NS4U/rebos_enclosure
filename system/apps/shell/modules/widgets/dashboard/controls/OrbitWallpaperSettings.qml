pragma ComponentBehavior: Bound
import QtQuick
import qs.config
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
    readonly property string accent: pending.accent ?? inFlight.accent ?? saved?.accent ?? "#d71921"
    readonly property string wellAction: pending.wellAction ?? inFlight.wellAction ?? saved?.wellAction ?? ""
    readonly property var wellActions: [
        { label: "Animation only", value: "" },
        { label: "App launcher", value: "launcher" },
        ...Array.from(DesktopEntries.applications.values, app => ({
            label: app.name, value: "app:" + app.id
        })).sort((a, b) => a.label.localeCompare(b.label))
    ]

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

    RowLayout {
        visible: typeof root.saved?.wellAction === "string"
        Layout.fillWidth: true
        StyledText { text: "Gravity well click"; Layout.fillWidth: true }
        SettingsComboBox {
            objectName: "orbit-well-action"
            Layout.preferredWidth: 240
            Accessible.name: "Gravity well click"
            model: root.wellActions
            textRole: "label"
            valueRole: "value"
            currentIndex: root.wellActions.findIndex(action => action.value === root.wellAction)
            onActivated: index => root.apply({wellAction: root.wellActions[index].value})
        }
    }

    ColorDialog {
        id: picker
        objectName: "orbit-picker"
        title: "Gravity well accent"
        onAccepted: root.apply({accent: String(selectedColor)})
    }

    StyledText {
        visible: root.checkedConnection && !root.saved
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        text: "The Orbit live wallpaper service is unavailable."
    }

    RowLayout {
        visible: !!root.saved
        Layout.fillWidth: true
        StyledText { text: "Gravity well accent"; Layout.fillWidth: true }
        Rectangle {
            implicitWidth: 24
            implicitHeight: 24
            radius: Styling.radius(-4)
            color: root.accent
            border.width: Config.controlBorderWidth
            border.color: Colors.outline
        }
        SettingsButton {
            objectName: "orbit-accent"
            text: root.accent.toUpperCase()
            Accessible.name: "Choose gravity well accent color"
            onClicked: {
                picker.selectedColor = root.accent;
                picker.open();
            }
        }
    }
}
