import QtQuick
import qs.modules.components
import qs.modules.services
import qs.modules.theme

// Arrow keys move between actions, and Enter activates the selection.
ActionGrid {
    id: root

    signal itemSelected

    layout: "row"
    labeledTiles: true
    buttonSize: Styling.spacing(60)
    iconSize: Styling.fontSize(6)
    spacing: Styling.spacing(8)
    focus: true

    Component.onCompleted: {
        root.forceActiveFocus();
    }

    actions: [
        {
            icon: Icons.lock,
            text: "Lock",
            tooltip: "Lock Session",
            command: ""
        },
        {
            icon: Icons.suspend,
            text: "Suspend",
            tooltip: "Suspend",
            command: "systemctl suspend"
        },
        {
            icon: Icons.hibernate,
            text: "Hibernate",
            tooltip: "Hibernate",
            command: "systemctl hibernate"
        },
        {
            icon: Icons.logout,
            text: "Log out",
            tooltip: "Log out",
            command: "niri msg action quit --skip-confirmation"
        },
        {
            icon: Icons.reboot,
            text: "Reboot",
            tooltip: "Reboot",
            command: "systemctl reboot"
        },
        {
            icon: Icons.shutdown,
            text: "Power off",
            variant: "error",
            tooltip: "Power Off",
            command: "systemctl poweroff"
        }
    ]

    onActionTriggered: action => {
        if (action.tooltip === "Lock Session")
            LockscreenService.lock();
        root.itemSelected();
    }
}
