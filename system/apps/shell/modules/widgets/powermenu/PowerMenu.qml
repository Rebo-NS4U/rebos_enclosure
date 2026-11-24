pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import qs.modules.components
import qs.modules.services
import qs.modules.theme
import qs.config

Item {
    id: root

    readonly property bool orbital: Styling.shellStyle === "orbital"
    signal itemSelected

    property int currentIndex: 0
    readonly property var actions: [
        { label: "Lock", glyph: Icons.lock, command: [] },
        { label: "Sleep", glyph: Icons.suspend, command: ["systemctl", "suspend"] },
        { label: "Shut down", glyph: Icons.shutdown, command: ["systemctl", "poweroff"] },
        { label: "Reboot", glyph: Icons.reboot, command: ["systemctl", "reboot"] },
        { label: "Log out", glyph: Icons.logout, command: ["niri", "msg", "action", "quit", "--skip-confirmation"] },
        { label: "Hibernate", glyph: Icons.hibernate, command: ["systemctl", "hibernate"] }
    ]

    implicitHeight: menuColumn.implicitHeight
    focus: true

    function activate(index: int) {
        const action = actions[index];
        if (action.command.length)
            Quickshell.execDetached(action.command);
        else
            LockscreenService.lock();
        itemSelected();
    }

    Keys.onPressed: event => {
        switch (event.key) {
        case Qt.Key_Up:
            currentIndex = (currentIndex + actions.length - actionGrid.columns) % actions.length;
            break;
        case Qt.Key_Left:
            currentIndex = (currentIndex + actions.length - 1) % actions.length;
            break;
        case Qt.Key_Down:
            currentIndex = (currentIndex + actionGrid.columns) % actions.length;
            break;
        case Qt.Key_Right:
            currentIndex = (currentIndex + 1) % actions.length;
            break;
        case Qt.Key_Return:
        case Qt.Key_Enter:
        case Qt.Key_Space:
            if (!event.isAutoRepeat)
                activate(currentIndex);
            break;
        default:
            return;
        }
        event.accepted = true;
    }

    Column {
        id: menuColumn
        width: parent.width
        spacing: Styling.spacing(16)

        StyledText {
            text: qsTr("Power menu")
            font.family: root.orbital ? "Departure Mono" : Config.theme.font
            font.pixelSize: Styling.fontSize(12)
            font.bold: true
        }

        Grid {
            id: actionGrid
            width: parent.width
            columns: root.orbital ? 2 : width >= Styling.spacing(500) ? 3 : 2
            spacing: Styling.spacing(8)

            Repeater {
                model: root.actions

                delegate: ThemeButton {
                    id: tile
                    required property int index
                    required property var modelData
                    width: (actionGrid.width - (actionGrid.columns - 1) * actionGrid.spacing) / actionGrid.columns
                    height: Styling.spacing(root.orbital ? 56 : 82)
                    text: modelData.label
                    highlighted: index === root.currentIndex
                    danger: modelData.command[1] === "poweroff"
                    focusPolicy: Qt.NoFocus
                    onClicked: root.activate(index)

                    contentItem: Column {
                        spacing: Styling.spacing(4)
                        topPadding: Math.max(0, (height - icon.height - label.height - spacing) / 2)

                        StyledText {
                            id: icon
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: tile.modelData.glyph
                            font.family: Icons.font
                            font.pixelSize: Styling.fontSize(10)
                            color: tile.danger && tile.background.variant !== "error" ? Colors.error : tile.background.itemColor
                        }

                        StyledText {
                            id: label
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: tile.text
                            color: tile.background.itemColor
                        }
                    }
                }
            }
        }

        StyledText {
            text: qsTr("↑ ↓ ← →  Select     Esc  Close")
            font.pixelSize: Styling.fontSize(-2)
            opacity: 0.75
        }
    }
}
