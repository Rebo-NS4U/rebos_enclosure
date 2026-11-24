pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.config
import qs.modules.components
import qs.modules.theme

ComboBox {
    id: root
    property bool previewFonts: false
    function selectFont(family) {
        activated(find(family, Qt.MatchExactly));
        popup.close();
    }

    wheelEnabled: false
    opacity: enabled ? 1 : 0.4
    implicitHeight: 48
    leftPadding: 14
    rightPadding: 36
    font.family: Config.theme.font
    font.pixelSize: Styling.fontSize(0)
    background: StyledRect {
        variant: root.hovered ? "focus" : "internalbg"
        radius: Styling.radius(-4)
        border.width: Config.controlBorderWidth
        border.color: root.activeFocus || root.popup.visible ? Colors.primary : Qt.alpha(Colors.outline, 0.3)
    }
    contentItem: TextField {
        text: root.editable ? root.editText : root.displayText
        enabled: root.editable
        readOnly: !root.editable
        selectByMouse: root.editable
        autoScroll: root.editable
        padding: 0
        background: null
        onTextEdited: root.editText = text
        color: root.enabled ? Colors.overSurface : Colors.overSurfaceVariant
        verticalAlignment: Text.AlignVCenter
        font: root.font
    }
    indicator: StyledText {
        x: root.width - width - 12
        anchors.verticalCenter: parent.verticalCenter
        text: Icons.caretDown
        font.family: Icons.font
        color: Colors.overSurfaceVariant
    }
    delegate: optionDelegate
    Component {
        id: optionDelegate
        ItemDelegate {
            id: option
            required property int index
            required property var modelData
            onClicked: {
                if (root.previewFonts)
                    root.selectFont(String(modelData));
            }
            width: root.width - 12
            implicitHeight: root.previewFonts ? 70 : 42
            padding: 12
            highlighted: (root.previewFonts ? fontOptions.currentIndex : root.highlightedIndex) === index
            hoverEnabled: true
            readonly property bool selected: root.previewFonts ? String(modelData) === root.currentText : index === root.currentIndex
            contentItem: StyledText {
                readonly property string label: root.textRole ? String(option.modelData[root.textRole] ?? "") : String(option.modelData)
                text: root.previewFonts ? label + "\nAa Bb Cc 0123456789" : label
                font.family: root.previewFonts ? label : root.font.family
                elide: Text.ElideRight
                color: option.selected ? Colors.primary : Colors.overSurface
                rightPadding: 24
                StyledText {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: option.selected ? "✓" : ""
                    color: Colors.primary
                }
            }
            background: StyledRect { variant: option.highlighted || option.hovered ? "focus" : "transparent"; radius: Math.max(0, Config.roundness) }
        }
    }
    popup: previewFonts ? fontPopup : optionsPopup

    component SettingsPopup: Popup {
        y: root.height + 6
        width: root.width
        padding: 6
        implicitHeight: Math.min(contentItem.implicitHeight + padding * 2, 300)
        background: StyledRect { variant: "popup"; radius: Styling.radius(-4) }
    }

    readonly property Popup optionsPopup: SettingsPopup {
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
            ScrollIndicator.vertical: ScrollIndicator {}
        }
    }

    readonly property Popup fontPopup: SettingsPopup {
        id: fontPicker
        focus: true
        onAboutToShow: fontSearch.clear()
        onOpened: {
            fontOptions.currentIndex = 0;
            fontSearch.forceActiveFocus();
        }
        contentItem: ColumnLayout {
            spacing: 6

            SettingsTextField {
                id: fontSearch
                Layout.fillWidth: true
                placeholderText: qsTr("Search fonts")
                onTextChanged: fontOptions.currentIndex = 0
                Keys.onDownPressed: fontOptions.incrementCurrentIndex()
                Keys.onUpPressed: fontOptions.decrementCurrentIndex()
                onAccepted: {
                    if (fontOptions.count > 0 && fontOptions.currentIndex >= 0)
                        root.selectFont(fontOptions.model[fontOptions.currentIndex]);
                }
            }

            ListView {
                id: fontOptions
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                implicitHeight: contentHeight
                model: {
                    if (!fontPicker.visible)
                        return [];
                    const query = fontSearch.text.trim().toLowerCase();
                    return root.model.filter(family => family.toLowerCase().includes(query));
                }
                delegate: optionDelegate
                boundsBehavior: Flickable.StopAtBounds
                ScrollIndicator.vertical: ScrollIndicator {}
            }
        }
    }
}
