import QtQuick
import Quickshell.Services.Notifications
import qs.modules.theme
import qs.modules.components

ThemeButton {
    id: root
    property bool visibleWhen: true
    property int urgency: NotificationUrgency.Normal

    anchors.fill: parent
    padding: 0
    visible: visibleWhen
    glyph: Icons.cancel
    danger: true
    emphasized: urgency === NotificationUrgency.Critical
    Accessible.name: "Dismiss notification"
}
