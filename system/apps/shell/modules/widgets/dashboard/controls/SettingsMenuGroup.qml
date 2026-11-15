pragma ComponentBehavior: Bound
import QtQuick

SettingsGroup {
    id: root
    property string entryPrefix: "settings-section-"
    required property var entries
    signal selected(string section)
    Repeater {
        model: root.entries
        delegate: SettingsSectionCard {
            required property var modelData
            objectName: root.entryPrefix + modelData.id
            text: modelData.label
            description: modelData.description
            glyph: modelData.glyph
            onClicked: root.selected(modelData.id)
        }
    }
}
