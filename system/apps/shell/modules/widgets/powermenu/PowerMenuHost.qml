pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.modules.services
import qs.modules.theme
import qs.config

// Fullscreen power menu for the invoking output.
Item {
    id: root

    required property var panel

    property bool menuOpen: false
    property real revealProgress: 0

    Behavior on revealProgress {
        enabled: Config.animDuration > 0
        NumberAnimation {
            duration: Config.animDuration
            easing.type: root.menuOpen ? Easing.OutCubic : Easing.InCubic
        }
    }

    readonly property bool popupOpen: menuOpen
    // Keep a tiny host for Visibilities registration; real UI is powerWindow.
    width: 1
    height: 1
    anchors.bottom: parent.bottom
    anchors.horizontalCenter: parent.horizontalCenter

    function togglePopup() {
        if (menuOpen)
            closeMenu();
        else
            openMenu();
    }

    function openMenu() {
        Visibilities.closeActiveBarPopup();
        Visibilities.clearAll();
        Visibilities.currentActiveModule = "";

        closeTimer.stop();
        menuOpen = true;
        powerWindow.visible = true;

        Qt.callLater(() => {
            if (!root.menuOpen)
                return;
            revealProgress = 1;
            powerMenuView.forceActiveFocus();
            powerMenuView.focusMenu();
        });
    }

    function closeMenu() {
        if (!menuOpen && !powerWindow.visible)
            return;

        menuOpen = false;
        revealProgress = 0;
        closeTimer.interval = Config.animDuration > 0
            ? Config.animDuration + 40
            : 40;
        closeTimer.restart();
    }

    Timer {
        id: closeTimer
        interval: 40
        onTriggered: {
            if (root.menuOpen)
                return;
            powerWindow.visible = false;
        }
    }

    PanelWindow {
        id: powerWindow
        screen: root.panel?.targetScreen ?? (Quickshell.screens.length > 0 ? Quickshell.screens[0] : null)
        visible: false

        WlrLayershell.namespace: "rebos_shell:powermenu"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: root.menuOpen ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
        exclusionMode: ExclusionMode.Ignore
        exclusiveZone: 0

        anchors.top: true
        anchors.bottom: true
        anchors.left: true
        anchors.right: true
        color: "transparent"

        FocusGrab {
            active: root.menuOpen
            windows: [powerWindow]
            onCleared: root.closeMenu()
        }

        Item {
            anchors.fill: parent
            opacity: root.revealProgress
            enabled: root.menuOpen

            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    GradientStop { position: 0; color: Qt.tint(Colors.background, Qt.alpha(Colors.primary, 0.17)) }
                    GradientStop { position: 0.62; color: Qt.alpha(Colors.background, 0.95) }
                    GradientStop { position: 1; color: Colors.background }
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: root.closeMenu()
            }

            Rectangle {
                anchors.fill: powerMenuView
                anchors.margins: -Styling.spacing(22)
                radius: Styling.radius(8)
                color: Qt.alpha(Colors.background, 0.86)
                border.color: Qt.alpha(Colors.outline, 0.4)
            }

            PowerMenuView {
                id: powerMenuView
                anchors.centerIn: parent
                width: Math.min(parent.width - Styling.spacing(60), Styling.spacing(600))
                popupMode: true
                expanded: root.menuOpen
                onCloseRequested: root.closeMenu()
            }
        }
    }

    Component.onCompleted: {
        const screenName = root.panel?.targetScreen?.name ?? "";
        if (screenName)
            Visibilities.registerPowerMenuButton(screenName, root);
    }

    Component.onDestruction: {
        const screenName = root.panel?.targetScreen?.name ?? "";
        if (screenName)
            Visibilities.unregisterPowerMenuButton(screenName, root);
    }
}
