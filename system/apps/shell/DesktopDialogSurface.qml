import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.components
import qs.modules.theme

StyledRect {
    id: surface
    required property var controller
    property alias searchInput: search
    property alias choiceList: list
    readonly property real contentImplicitHeight: content.implicitHeight + Styling.spacing(32)
    implicitHeight: contentImplicitHeight
    variant: "popup"
    radius: Styling.radius(0)
    enableShadow: true
    function reveal(item) {
        const position = item.mapToItem(content, 0, 0);
        const bottom = position.y + item.height;
        if (position.y < viewport.contentY) viewport.contentY = Math.max(0, position.y);
        else if (bottom > viewport.contentY + viewport.height)
            viewport.contentY = Math.min(Math.max(0, viewport.contentHeight - viewport.height), bottom - viewport.height);
    }
    Flickable {
        id: viewport
        ScrollBar.vertical: ScrollBar {}
        anchors.fill: parent
        anchors.margins: Styling.spacing(16)
        contentHeight: content.implicitHeight
        clip: true
        ColumnLayout {
            id: content
            width: viewport.width
            spacing: Styling.spacing(12)
            focus: true
            Keys.onEscapePressed: controller.cancel()
            StyledText {
                color: surface.itemColor
                Layout.fillWidth: true
                text: controller.authenticating ? "Authentication required" : controller.request?.title ?? "Select"
                font.bold: true
                wrapMode: Text.Wrap
            }
            StyledText {
                color: surface.itemColor
                Layout.fillWidth: true
                visible: controller.authenticating
                text: controller.flow?.message ?? ""
                wrapMode: Text.Wrap
            }
            Flow {
                Layout.fillWidth: true
                spacing: Styling.spacing(8)
                visible: controller.authenticating && (controller.flow?.identities.length ?? 0) > 1
                Repeater {
                    model: controller.flow?.identities ?? []
                    ThemeButton {
                        required property var modelData
                        text: modelData.displayName || modelData.name || "User"
                        checked: controller.flow?.selectedIdentity === modelData
                        onClicked: { search.clear(); controller.flow.selectedIdentity = modelData; }
                    }
                }
            }
            StyledText {
                Layout.fillWidth: true
                visible: controller.authenticating && text.length > 0
                text: controller.flow?.supplementaryMessage || (controller.flow?.failed ? "Authentication failed. Try again or cancel." : "")
                color: controller.flow?.supplementaryIsError || controller.flow?.failed ? Colors.error : surface.itemColor
                wrapMode: Text.Wrap
            }
            StyledText {
                color: surface.itemColor
                Layout.fillWidth: true
                visible: controller.authenticating
                text: controller.flow?.inputPrompt || "Waiting for authentication…"
                wrapMode: Text.Wrap
            }
            SearchInput {
                id: search
                Layout.fillWidth: true
                implicitHeight: Math.max(Styling.spacing(48), Styling.fontSize(0) + Styling.spacing(20))
                border.width: 3
                border.color: inputActiveFocus ? Colors.primary : Qt.alpha(Colors.outline, 0.3)
                Accessible.name: controller.authenticating ? "Authentication response" : "Search choices"
                enabled: !controller.authenticating || (controller.flow?.isResponseRequired ?? false)
                passwordMode: controller.authenticating && !controller.flow?.responseVisible
                placeholderText: controller.authenticating ? "Authentication response" : controller.request?.placeholder ?? "Search…"
                clearOnEscape: false
                onInputActiveFocusChanged: if (inputActiveFocus) surface.reveal(search)
                onSearchTextChanged: if (!controller.authenticating) controller.filter()
                onAccepted: controller.submit()
                onEscapePressed: controller.cancel()
                onDownPressed: list.currentIndex = Math.min(controller.choices.length - 1, list.currentIndex + 1)
                onUpPressed: list.currentIndex = Math.max(0, list.currentIndex - 1)
            }
            ListView {
                id: list
                visible: !controller.authenticating
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(Styling.spacing(320), contentHeight)
                clip: true
                model: controller.choices
                currentIndex: -1
                onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)
                delegate: ThemeButton {
                    required property string modelData
                    required property int index
                    width: list.width
                    text: modelData
                    highlighted: list.currentIndex === index
                    onActiveFocusChanged: if (activeFocus) surface.reveal(this)
                    onClicked: controller.finish(modelData)
                }
            }
            StyledText {
                color: surface.itemColor
                visible: !controller.authenticating && controller.choices.length === 0
                text: "No matching entries"
            }
            Flow {
                Layout.fillWidth: true
                spacing: Styling.spacing(8)
                ThemeButton { text: "Cancel"; onActiveFocusChanged: if (activeFocus) surface.reveal(this); onClicked: controller.cancel() }
                ThemeButton {
                    onActiveFocusChanged: if (activeFocus) surface.reveal(this)
                    text: controller.authenticating ? "Authenticate" : "Select"
                    highlighted: true
                    enabled: controller.authenticating ? controller.flow?.isResponseRequired ?? false : list.currentIndex >= 0
                    onClicked: controller.submit()
                }
            }
        }
    }
}
