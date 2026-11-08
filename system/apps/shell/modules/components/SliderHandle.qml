import QtQuick
import qs.modules.theme
Rectangle {
    property bool focused: false
    implicitWidth: 16
    implicitHeight: 16
    radius: width / 2
    color: Colors.primary
    border.width: focused ? 2 : 0
    border.color: Colors.overSurface
}
