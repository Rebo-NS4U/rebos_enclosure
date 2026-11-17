import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.components
import qs.modules.services
import qs.modules.theme

ColumnLayout {
    id: root
    objectName: "audio-eq-presets"
    spacing: Styling.spacing(6)
    property string category: AudioEqualizer.presetGroups.Other.includes(AudioEqualizer.preset) ? "Other" : "Music"
    readonly property var choices: AudioEqualizer.presetGroups[category]
    function revealSelection() {
        const selected = choices.indexOf(AudioEqualizer.preset);
        cards.currentIndex = Math.max(0, selected);
        cards.positionViewAtIndex(cards.currentIndex, ListView.Contain);
    }
    function choose(name) { AudioEqualizer.selectPreset(name); }
    onCategoryChanged: Qt.callLater(revealSelection)
    Connections {
        target: AudioEqualizer
        function onPresetChanged() {
            if (AudioEqualizer.presetGroups.Other.includes(AudioEqualizer.preset)) root.category = "Other";
            else if (AudioEqualizer.presetGroups.Music.includes(AudioEqualizer.preset)) root.category = "Music";
            Qt.callLater(root.revealSelection);
        }
    }
    Component.onCompleted: Qt.callLater(revealSelection)
    RowLayout {
        Layout.fillWidth: true
        spacing: Styling.spacing(6)
        ThemeButton {
            objectName: "audio-eq-category-Music"
            text: "Music"
            checked: root.category === "Music"
            onClicked: root.category = "Music"
        }
        ThemeButton {
            objectName: "audio-eq-category-Other"
            text: "Other"
            checked: root.category === "Other"
            onClicked: root.category = "Other"
        }
        StyledText {
            Layout.fillWidth: true
            text: AudioEqualizer.preset
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
            Accessible.name: "Current equalizer preset: " + text
        }
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: Styling.spacing(4)
        ThemeButton {
            text: "‹"
            Accessible.name: "Previous presets"
            enabled: cards.contentX > 1
            onClicked: cards.positionViewAtIndex(Math.max(0, cards.indexAt(cards.contentX + 1, 1) - 1), ListView.Beginning)
        }
        ListView {
            id: cards
            objectName: "audio-eq-preset-cards"
            Layout.fillWidth: true
            Layout.preferredHeight: Styling.spacing(64)
            orientation: ListView.Horizontal
            spacing: Styling.spacing(6)
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: root.choices
            currentIndex: 0
            delegate: ThemeButton {
                required property string modelData
                required property int index
                objectName: "audio-eq-preset-" + modelData
                width: Math.min(cards.width, Styling.spacing(148))
                height: cards.height
                checked: AudioEqualizer.preset === modelData
                Accessible.name: modelData + ": " + AudioEqualizer.presetDescriptions[modelData]
                onClicked: root.choose(modelData)
                onActiveFocusChanged: if (activeFocus) cards.positionViewAtIndex(index, ListView.Contain)
                Keys.onLeftPressed: { cards.currentIndex = Math.max(0, index - 1); cards.itemAtIndex(cards.currentIndex)?.forceActiveFocus(); }
                Keys.onRightPressed: { cards.currentIndex = Math.min(root.choices.length - 1, index + 1); cards.positionViewAtIndex(cards.currentIndex, ListView.Contain); Qt.callLater(() => cards.itemAtIndex(cards.currentIndex)?.forceActiveFocus()); }
                contentItem: ColumnLayout {
                    spacing: Styling.spacing(2)
                    StyledText { objectName: "preset-card-label"; text: modelData; font.bold: true; color: parent.parent.background.itemColor; Layout.fillWidth: true; elide: Text.ElideRight }
                    StyledText { text: AudioEqualizer.presetDescriptions[modelData]; font.pixelSize: Styling.fontSize(-3); color: parent.parent.background.itemColor; Layout.fillWidth: true; elide: Text.ElideRight }
                }
            }
        }
        ThemeButton {
            text: "›"
            Accessible.name: "Next presets"
            enabled: !cards.atXEnd
            onClicked: {
                const first = Math.max(0, cards.indexAt(cards.contentX + 1, 1));
                cards.positionViewAtIndex(Math.min(root.choices.length - 1, first + Math.max(1, Math.floor(cards.width / Styling.spacing(154)))), ListView.Beginning);
            }
        }
    }
}
