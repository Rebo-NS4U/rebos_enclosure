pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Wayland._BackgroundEffect
import Quickshell.Wayland
import qs.modules.components
import qs.modules.services
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
        BackgroundEffect.blurRegion: BlurRegion { target: powerBackdrop }
        color: "transparent"

        FocusGrab {
            active: root.menuOpen
            windows: [powerWindow]
            onCleared: root.closeMenu()
        }

        StyledRect {
            id: powerBackdrop
            anchors.fill: parent
            variant: "popup"
            radius: 0
            enableBorder: false
            opacity: root.revealProgress
            enabled: root.menuOpen

            MouseArea {
                anchors.fill: parent
                onClicked: root.closeMenu()
            }

            PowerMenuView {
                id: powerMenuView
                anchors.centerIn: parent
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
