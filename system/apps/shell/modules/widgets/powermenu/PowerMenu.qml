pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import qs.modules.components
import qs.modules.services
import qs.config

Item {
    id: root

    signal itemSelected

    property int currentIndex: 0
    readonly property var actions: [
        { label: "Lock", command: [] },
        { label: "Sleep", command: ["systemctl", "suspend"] },
        { label: "Shut down", command: ["systemctl", "poweroff"] },
        { label: "Reboot", command: ["systemctl", "reboot"] },
        { label: "Log out", command: ["niri", "msg", "action", "quit", "--skip-confirmation"] },
        { label: "Hibernate", command: ["systemctl", "hibernate"] }
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
        case Qt.Key_Left:
            currentIndex = (currentIndex + actions.length - 1) % actions.length;
            break;
        case Qt.Key_Down:
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

    FontLoader {
        id: dotTypeface
        source: "../../theme/fonts/Doto.ttf"
    }

    Column {
        id: menuColumn
        width: parent.width

        Repeater {
            model: root.actions

            delegate: Item {
                id: row
                required property int index
                required property var modelData
                readonly property bool selected: index === root.currentIndex

                width: menuColumn.width
                height: width * (selected ? 0.16 : 0.085)
                Accessible.role: Accessible.Button
                Accessible.name: modelData.label
                Accessible.focused: selected && root.activeFocus
                Accessible.onPressAction: root.activate(index)

                Rectangle {
                    visible: row.selected
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: row.width * 0.025
                    height: width
                    radius: width / 2
                    color: "#e51e2a"
                    antialiasing: true
                }

                StyledText {
                    anchors.left: parent.left
                    anchors.leftMargin: row.selected ? row.width * 0.055 : 0
                    anchors.verticalCenter: parent.verticalCenter
                    text: row.modelData.label.toUpperCase()
                    font.family: dotTypeface.status === FontLoader.Ready ? dotTypeface.name : Config.theme.monoFont
                    font.pixelSize: Math.max(1, Math.round(row.width * (row.selected ? 0.16 : 0.065)))
                    font.variableAxes: ({ "ROND": 100, "wght": row.selected ? 800 : 500 })
                    color: row.selected ? "#ffffff" : pointer.containsMouse ? "#cccccc" : "#858585"
                }

                MouseArea {
                    id: pointer
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.activate(row.index)
                }
            }
        }
    }
}
