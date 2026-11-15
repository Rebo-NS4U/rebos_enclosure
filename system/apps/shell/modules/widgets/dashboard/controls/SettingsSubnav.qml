pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

Flow {
    id: root
    required property var sections
    required property string currentSection
    signal selected(string section)
    Layout.fillWidth: true
    spacing: 8
    Repeater {
        model: root.sections
        delegate: SettingsButton {
            required property var modelData
            objectName: "settings-subpage-" + modelData.id
            text: modelData.label
            highlighted: root.currentSection === modelData.id
            onClicked: root.selected(modelData.id)
        }
    }
}
