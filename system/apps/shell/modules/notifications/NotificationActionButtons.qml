import QtQuick
import QtQuick.Layouts
import Quickshell.Services.Notifications
import qs.modules.theme
import qs.modules.components
import qs.modules.services

Item {
    id: root
    property var actions: []
    property bool showWhen: true
    property var notificationObject: null
    property int urgency: NotificationUrgency.Normal

    Layout.fillWidth: true
    readonly property var validActions: actions.filter(action => action && String(action.text || "").trim() !== "")
    implicitHeight: showWhen && validActions.length > 0 ? 32 : 0
    height: implicitHeight
    clip: true

    RowLayout {
        anchors.fill: parent
        spacing: Styling.spacing(4)

        Repeater {
            model: root.validActions

            ThemeButton {
                Layout.fillWidth: true
                Layout.preferredHeight: 32

                text: modelData.text
                font.weight: Font.DemiBold
                padding: Styling.spacing(4)
                danger: root.urgency === NotificationUrgency.Critical
                emphasized: danger

                onClicked: {
                    if (root.notificationObject) {
                        Notifications.attemptInvokeAction(root.notificationObject.id, modelData.identifier);
                    }
                }
            }
        }
    }
}
