pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.modules.theme
import qs.modules.components
import qs.modules.services
import qs.config

Item {
    id: root

    implicitWidth: Styling.spacing(440)
    implicitHeight: mainColumn.implicitHeight + Styling.spacing(36)

    signal backRequested()
    signal actionTriggered()

    // Keyboard selection: -1 = none. IslandBar routes Left/Right/Return here.
    property int selectedIndex: -1
    readonly property var actions: [
        { label: "Suspend", icon: Icons.suspend, run: root.doSuspend },
        { label: "Lock", icon: Icons.lock, run: root.doLock },
        { label: "Log out", icon: Icons.logout, run: root.doLogout },
        { label: "Reboot", icon: Icons.reboot, run: root.doReboot },
        { label: "Power off", icon: Icons.shutdown, run: root.doShutdown, danger: true }
    ]
    readonly property int actionCount: actions.length

    function resetSelection() {
        selectedIndex = -1;
    }

    function moveSelection(delta: int) {
        selectedIndex = (((selectedIndex + delta) % actionCount) + actionCount) % actionCount;
    }

    function activateSelected() {
        if (selectedIndex >= 0 && selectedIndex < actionCount)
            actions[selectedIndex].run();
    }

    function doSuspend() {
        Quickshell.execDetached(["systemctl", "suspend"]);
        root.actionTriggered();
    }

    function doLock() {
        LockscreenService.lock();
        root.actionTriggered();
    }

    function doLogout() {
        Quickshell.execDetached(["niri", "msg", "action", "quit", "--skip-confirmation"]);
        root.actionTriggered();
    }

    function doReboot() {
        Quickshell.execDetached(["systemctl", "reboot"]);
        root.actionTriggered();
    }

    function doShutdown() {
        Quickshell.execDetached(["systemctl", "poweroff"]);
        root.actionTriggered();
    }

    onVisibleChanged: {
        if (!visible)
            resetSelection();
    }

    ColumnLayout {
        id: mainColumn
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Styling.spacing(18)
        spacing: Styling.spacing(12)

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(8)

            IslandBackButton {
                onClicked: root.backRequested()
            }

            Text {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                text: "Power"
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(3)
                font.bold: true
                color: Colors.overBackground
            }

            Item { Layout.fillWidth: true }
        }

        Separator { Layout.fillWidth: true; implicitHeight: 1 }

        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(8)

            Repeater {
                model: root.actions

                Button {
                    id: actionButton
                    required property int index
                    required property var modelData

                    readonly property bool selected: root.selectedIndex === index || hovered
                    readonly property bool danger: modelData.danger === true

                    Layout.fillWidth: true
                    Layout.preferredWidth: Styling.spacing(72)
                    Layout.minimumWidth: label.implicitWidth + Styling.spacing(12)
                    Layout.preferredHeight: Styling.spacing(60)
                    text: modelData.label
                    Accessible.name: text
                    hoverEnabled: true
                    focusPolicy: Qt.NoFocus
                    scale: down ? 0.93 : 1
                    onClicked: modelData.run()

                    Behavior on scale {
                        enabled: Config.animDuration > 0
                        NumberAnimation {
                            duration: actionButton.down ? Motion.press : Motion.feedback
                            easing.type: Motion.feedbackCurve
                        }
                    }

                    background: StyledRect {
                        id: tileSurface
                        radius: Styling.radius(-4)
                        buttonSurface: true
                        controlPressed: actionButton.down
                        variant: actionButton.selected ? (actionButton.danger ? "error" : "primary") : "common"
                        border.width: actionButton.selected ? 2 : 1
                        border.color: actionButton.selected ? itemColor : Qt.alpha(Colors.outline, 0.3)
                    }

                    contentItem: Item {
                        Column {
                            anchors.centerIn: parent
                            spacing: Styling.spacing(4)

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: actionButton.modelData.icon
                                textFormat: Text.RichText
                                font.family: Icons.font
                                font.pixelSize: Styling.fontSize(6)
                                color: actionButton.danger && !actionButton.selected ? Colors.error : tileSurface.itemColor
                            }

                            StyledText {
                                id: label
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: actionButton.text
                                font.pixelSize: Styling.fontSize(-2)
                                font.weight: Font.DemiBold
                                color: tileSurface.itemColor
                            }
                        }
                    }
                }
            }
        }
    }
}
