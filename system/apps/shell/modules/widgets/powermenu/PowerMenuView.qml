import QtQuick
import qs.modules.services

Item {
    id: root

    implicitHeight: powerMenu.implicitHeight
    property bool popupMode: false
    property bool expanded: true
    focus: true

    signal closeRequested()

    function focusMenu() {
        powerMenu.currentIndex = 0;
        powerMenu.forceActiveFocus();
    }

    PowerMenu {
        id: powerMenu
        anchors.fill: parent

        onItemSelected: {
            if (root.popupMode)
                root.closeRequested();
            else
                Visibilities.setActiveModule("");
        }
    }

    Keys.onPressed: event => {
        if (event.key === Qt.Key_Escape) {
            if (root.popupMode)
                root.closeRequested();
            else
                Visibilities.setActiveModule("");
            event.accepted = true;
        }
    }

    onExpandedChanged: {
        if (expanded)
            Qt.callLater(() => root.focusMenu());
    }

    onVisibleChanged: {
        if (visible)
            Qt.callLater(() => root.focusMenu());
    }

    Component.onCompleted: {
        if (visible)
            Qt.callLater(() => root.focusMenu());
    }
}
