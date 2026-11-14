pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.modules.theme
import qs.modules.components
import qs.modules.widgets.dashboard.widgets.calendar
import qs.config

Item {
    id: root

    implicitWidth: Styling.spacing(440)
    implicitHeight: mainCol.implicitHeight + Styling.spacing(36)

    signal backRequested()

    property date now: new Date()

    Timer {
        interval: 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.now = new Date()
    }

    ColumnLayout {
        id: mainCol
        anchors.fill: parent
        anchors.margins: Styling.spacing(18)
        spacing: Styling.spacing(14)

        // ═══════════════════════════════════════════════════════════════
        // HEADER: Back button + Title
        // ═══════════════════════════════════════════════════════════════
        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(8)

            IslandBackButton {
                onClicked: root.backRequested()
            }

            Text {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                text: "Calendar"
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(3)
                font.bold: true
                color: Colors.overBackground
            }

            Item { Layout.fillWidth: true }
        }

        Separator { Layout.fillWidth: true; implicitHeight: 1 }

        // ═══════════════════════════════════════════════════════════════
        // CLOCK CARD: One clean clock on top of the calendar
        // ═══════════════════════════════════════════════════════════════
        StyledRect {
            id: clockCard
            Layout.fillWidth: true
            implicitHeight: 60
            radius: Styling.radius(2)
            variant: "internalbg"
            clip: true

            RowLayout {
                id: clockCol
                anchors.centerIn: parent

                Text {
                    id: clockText
                    renderType: Text.NativeRendering
                    font.hintingPreference: Font.PreferFullHinting
                    text: Qt.formatTime(root.now, Config.bar?.use12hFormat ? "hh:mm:ss ap" : "hh:mm:ss")
                    font.family: Config.theme.monoFont
                    font.pixelSize: Styling.fontSize(10)
                    font.bold: true
                    color: Colors.overBackground
                }
            }
        }

        // ═══════════════════════════════════════════════════════════════
        // CALENDAR: Reused standard calendar component
        // ═══════════════════════════════════════════════════════════════
        Calendar {
            Layout.fillWidth: true
            Layout.preferredHeight: 265
        }
    }
}
