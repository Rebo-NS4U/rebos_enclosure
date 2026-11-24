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
    readonly property string accent: pending.accent ?? inFlight.accent ?? saved?.accent ?? "#d71921"

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
            border.width: 3
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
