import QtQuick
import qs.modules.theme

Rectangle {
    id: root

    property bool focused: false
    property bool vertical: false
    property color accent: Colors.primary

    // Equal bounds keep Qt Quick Controls' slider mapping centered on the grip.
    implicitWidth: 14
    implicitHeight: 14
    color: "transparent"

    Rectangle {
        anchors.centerIn: parent
        width: root.vertical ? 18 : 5
        height: root.vertical ? 5 : 18
        radius: 2
        color: root.focused ? Colors.overSurface : root.accent
        border.width: 3
        border.color: Colors.surface
    }
}
