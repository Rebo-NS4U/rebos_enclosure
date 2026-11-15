import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.components
import qs.modules.services
import qs.modules.theme

Button {
    id: root
    objectName: "bar-release-update"
    visible: EnclosureUpdates.release.available || EnclosureUpdates.running
    enabled: !EnclosureUpdates.running
    implicitHeight: 36
    implicitWidth: label.implicitWidth + 24
    Layout.alignment: Qt.AlignVCenter
    Accessible.name: text
    text: EnclosureUpdates.running ? "Updating…" : "Update available"
    onClicked: EnclosureUpdates.apply()
    background: StyledRect {
        variant: root.hovered || root.activeFocus ? "focus" : "primary"
        radius: Styling.radius(4)
        border.width: root.activeFocus ? 2 : 0
        border.color: Colors.primary
    }
    contentItem: StyledText {
        id: label
        text: root.text
        color: root.hovered || root.activeFocus ? Colors.primary : Colors.overPrimary
        font.bold: true
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignHCenter
    }
    StyledToolTip {
        show: root.hovered
        tooltipText: "Enclosure " + (EnclosureUpdates.release.tag || "")
        description: EnclosureUpdates.feedback || "Click to install this release with progress and recovery backups."
    }
}
