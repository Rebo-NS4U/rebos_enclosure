pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import qs.config
import qs.modules.components
import qs.modules.theme

ComboBox {
    id: root
    property bool previewFonts: false
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
        border.width: root.activeFocus || root.popup.visible ? 2 : 1
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
    delegate: ItemDelegate {
        id: option
        required property int index
        required property var modelData
        width: root.width - 12
        implicitHeight: root.previewFonts ? 70 : 42
        padding: 12
        highlighted: root.highlightedIndex === index
        hoverEnabled: true
        contentItem: StyledText {
            readonly property string label: root.textRole ? String(option.modelData[root.textRole] ?? "") : String(option.modelData)
            text: root.previewFonts ? label + "\nAa Bb Cc 0123456789" : label
            font.family: root.previewFonts ? label : root.font.family
            elide: Text.ElideRight
            color: option.index === root.currentIndex ? Colors.primary : Colors.overSurface
            rightPadding: 24
            StyledText {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: option.index === root.currentIndex ? "✓" : ""
                color: Colors.primary
            }
        }
        background: StyledRect { variant: option.highlighted || option.hovered ? "focus" : "transparent"; radius: Math.max(0, Config.roundness) }
    }
    popup: Popup {
        y: root.height + 6
        width: root.width
        padding: 6
        implicitHeight: Math.min(contentItem.implicitHeight + padding * 2, 300)
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
            ScrollIndicator.vertical: ScrollIndicator {}
        }
        background: StyledRect { variant: "popup"; radius: Styling.radius(-4) }
    }
}
