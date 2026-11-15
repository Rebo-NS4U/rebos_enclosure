pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.theme
import qs.modules.components
import qs.config

Item {
    id: root
    property int maxContentWidth: 760
    property string currentSection: "weather"
    Flickable {
        anchors.fill: parent
        contentHeight: body.implicitHeight
        clip: true
        ScrollBar.vertical: ScrollBar {}
        ColumnLayout {
            id: body
            width: Math.min(root.width, root.maxContentWidth)
            anchors.horizontalCenter: parent.horizontalCenter
            WeatherSettings { visible: root.currentSection === "weather" || root.currentSection === "" }
            PerformanceSettings { visible: root.currentSection === "performance" }
            StorageSettings { visible: root.currentSection === "system" }
        }
    }
}
