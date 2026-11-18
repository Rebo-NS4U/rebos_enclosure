import QtQuick
import QtQuick.Layouts
import qs.modules.components
import qs.modules.services
import qs.modules.theme

ThemeButton {
    id: root
    objectName: "bar-release-update"
    visible: EnclosureUpdates.release.available || EnclosureUpdates.running
    enabled: !EnclosureUpdates.running
    emphasized: true
    font.bold: true
    Layout.alignment: Qt.AlignVCenter
    Accessible.name: text
    text: EnclosureUpdates.running ? "Updating…" : "Update available"
    onClicked: EnclosureUpdates.apply()
    StyledToolTip {
        show: root.hovered
        tooltipText: "Enclosure " + (EnclosureUpdates.release.tag || "")
        description: EnclosureUpdates.feedback || "Click to install this release with progress and recovery backups."
    }
}
