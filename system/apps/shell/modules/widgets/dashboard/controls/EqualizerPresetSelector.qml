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
    readonly property int cardsPerPage: Math.max(1, Math.min(3, Math.floor((pages.width + Styling.spacing(6)) / Styling.spacing(145))))
    readonly property int pageCount: Math.ceil(choices.length / cardsPerPage)
    readonly property int currentPage: pages.currentIndex
    function revealSelection() {
        const selected = choices.indexOf(AudioEqualizer.preset);
        pages.currentIndex = selected >= 0 ? Math.floor(selected / cardsPerPage) : 0;
        pages.positionViewAtIndex(pages.currentIndex, ListView.Beginning);
    }
    function pageBy(direction) {
        pages.currentIndex = Math.max(0, Math.min(pageCount - 1, pages.currentIndex + direction));
        pages.positionViewAtIndex(pages.currentIndex, ListView.Beginning);
    }
    function focusCard(index) {
        index = Math.max(0, Math.min(choices.length - 1, index));
        pages.currentIndex = Math.floor(index / cardsPerPage);
        pages.positionViewAtIndex(pages.currentIndex, ListView.Beginning);
        Qt.callLater(() => {
            const page = pages.itemAtIndex(pages.currentIndex);
            page?.cardRepeater.itemAt(index % cardsPerPage)?.forceActiveFocus();
        });
    }
    onCategoryChanged: Qt.callLater(revealSelection)
    onCardsPerPageChanged: Qt.callLater(revealSelection)
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
            text: AudioEqualizer.preset + " · " + (pages.currentIndex + 1) + "/" + root.pageCount
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
            Accessible.name: "Current preset: " + AudioEqualizer.preset + ". Page " + (pages.currentIndex + 1) + " of " + root.pageCount
        }
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: Styling.spacing(6)
        ThemeButton {
            objectName: "audio-eq-previous-page"
            text: "‹"
            Layout.preferredWidth: Styling.spacing(36)
            Layout.preferredHeight: pages.height
            Accessible.name: "Previous preset page"
            enabled: pages.currentIndex > 0
            onClicked: root.pageBy(-1)
        }
        ListView {
            id: pages
            objectName: "audio-eq-preset-cards"
            Layout.fillWidth: true
            Layout.preferredHeight: Styling.spacing(68)
            orientation: ListView.Horizontal
            snapMode: ListView.SnapOneItem
            highlightRangeMode: ListView.StrictlyEnforceRange
            highlightMoveDuration: Motion.enabled ? Motion.feedback : 0
            preferredHighlightBegin: 0
            preferredHighlightEnd: width
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: root.pageCount
            currentIndex: 0
            WheelHandler {
                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                onWheel: event => {
                    const delta = Math.abs(event.angleDelta.x) > Math.abs(event.angleDelta.y) ? event.angleDelta.x : event.angleDelta.y;
                    if (delta && !wheelDebounce.running) { root.pageBy(delta < 0 ? 1 : -1); wheelDebounce.start(); }
                    event.accepted = true;
                }
            }
            Timer { id: wheelDebounce; interval:180 }
            delegate: Row {
                id: page
                required property int index
                property alias cardRepeater: cardRepeater
                width: pages.width
                height: pages.height
                spacing: Styling.spacing(6)
                Repeater {
                    id: cardRepeater
                    model: Math.min(root.cardsPerPage, root.choices.length - page.index * root.cardsPerPage)
                    ThemeButton {
                        id: card
                        required property int index
                        readonly property int choiceIndex: page.index * root.cardsPerPage + index
                        readonly property string choice: root.choices[choiceIndex] || ""
                        objectName: "audio-eq-preset-" + choice
                        width: (pages.width - (root.cardsPerPage - 1) * page.spacing) / root.cardsPerPage
                        height: pages.height
                        checked: AudioEqualizer.preset === choice
                        Accessible.name: choice + ": " + AudioEqualizer.presetDescriptions[choice]
                        onClicked: AudioEqualizer.selectPreset(choice)
                        onActiveFocusChanged: if (activeFocus && pages.currentIndex !== page.index) {
                            pages.currentIndex = page.index;
                            pages.positionViewAtIndex(page.index, ListView.Beginning);
                        }
                        Keys.onLeftPressed: root.focusCard(choiceIndex - 1)
                        Keys.onRightPressed: root.focusCard(choiceIndex + 1)
                        Keys.onPressed: event => {
                            if (event.key === Qt.Key_Home) root.focusCard(0);
                            else if (event.key === Qt.Key_End) root.focusCard(root.choices.length - 1);
                            else if (event.key === Qt.Key_PageUp) root.focusCard(choiceIndex - root.cardsPerPage);
                            else if (event.key === Qt.Key_PageDown) root.focusCard(choiceIndex + root.cardsPerPage);
                            else { event.accepted = false; return; }
                            event.accepted = true;
                        }
                        contentItem: ColumnLayout {
                            spacing: Styling.spacing(2)
                            StyledText {
                                objectName: "preset-card-label"
                                text: (card.checked ? "✓ " : "") + card.choice
                                font.bold: true
                                color: card.background.itemColor
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            StyledText {
                                text: AudioEqualizer.presetDescriptions[card.choice] || ""
                                font.pixelSize: Styling.fontSize(-3)
                                color: card.background.itemColor
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                            }
                        }

                    }
                }
            }
        }
        ThemeButton {
            objectName: "audio-eq-next-page"
            text: "›"
            Layout.preferredWidth: Styling.spacing(36)
            Layout.preferredHeight: pages.height
            Accessible.name: "Next preset page"
            enabled: pages.currentIndex < root.pageCount - 1
            onClicked: root.pageBy(1)
        }
    }
}
