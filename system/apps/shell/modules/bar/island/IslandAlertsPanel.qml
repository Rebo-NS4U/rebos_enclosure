pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Widgets
import qs.modules.theme
import qs.modules.components
import qs.modules.services
import qs.modules.globals
import qs.modules.notifications
import qs.config

Item {
    id: root

    implicitWidth: Styling.spacing(480)
    implicitHeight: Styling.spacing(500)

    signal backRequested()

    readonly property int totalCount: {
        let count = 0;
        const list = Notifications.appNameList;
        for (let i = 0; i < list.length; i++) {
            const grp = Notifications.groupsByAppName[list[i]];
            if (grp?.notifications)
                count += grp.notifications.length;
        }
        return count;
    }

    property var cascadeItems: []
    property int cascadeIndex: 0
    property bool isClearing: false

    function discardAllWithAnimation() {
        if (isClearing) return;

        const children = notificationList.contentItem.children;
        if (!children || children.length === 0) {
            Notifications.discardAllNotifications();
            return;
        }

        cascadeItems = [];
        for (let i = 0; i < children.length; i++) {
            if (children[i] && children[i].destroyWithAnimation) {
                cascadeItems.push(children[i]);
            }
        }

        if (cascadeItems.length === 0) {
            Notifications.discardAllNotifications();
            return;
        }

        isClearing = true;
        cascadeIndex = 0;

        // Animate first item immediately
        const first = cascadeItems[0];
        if (first && first.destroyWithAnimation) {
            first.destroyWithAnimation(true);
        }
        cascadeIndex = 1;

        if (cascadeItems.length > 1) {
            cascadeTimer.restart();
        } else {
            discardAllTimer.interval = Math.max(Config.animDuration || 240, 150) + 40;
            discardAllTimer.restart();
        }
    }

    Timer {
        id: cascadeTimer
        interval: 45
        repeat: true
        onTriggered: {
            if (cascadeIndex < cascadeItems.length) {
                const item = cascadeItems[cascadeIndex];
                if (item && item.destroyWithAnimation) {
                    item.destroyWithAnimation(true);
                }
                cascadeIndex++;
            } else {
                stop();
                const totalDelay = Math.max(Config.animDuration || 240, 150) + 40;
                discardAllTimer.interval = totalDelay;
                discardAllTimer.restart();
            }
        }
    }

    Timer {
        id: discardAllTimer
        interval: Math.max(Config.animDuration || 240, 150) + 40
        repeat: false
        onTriggered: {
            Notifications.discardAllNotifications();
            isClearing = false;
            cascadeItems = [];
        }
    }

    onVisibleChanged: {
        if (!visible && isClearing) {
            cascadeTimer.stop();
            discardAllTimer.stop();
            Notifications.discardAllNotifications();
            isClearing = false;
            cascadeItems = [];
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Styling.spacing(18)
        spacing: Styling.spacing(14)

        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(8)

            // Back button
            IslandBackButton {
                onClicked: root.backRequested()
            }

            // Title
            Text {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                text: "Notifications"
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(3)
                font.bold: true
                color: Colors.overBackground
            }

            // Count Pill
            StyledRect {
                visible: root.totalCount > 0
                implicitWidth: countText.implicitWidth + 12
                implicitHeight: 20
                radius: Styling.radius(0)
                variant: "primary"

                Text {
                    id: countText
                    anchors.centerIn: parent
                    renderType: Text.NativeRendering
                    font.hintingPreference: Font.PreferFullHinting
                    text: root.totalCount.toString()
                    font.family: Config.theme.monoFont
                    font.pixelSize: Styling.fontSize(-3)
                    font.bold: true
                    color: Colors.overPrimary
                }
            }

            Item { Layout.fillWidth: true }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(8)

            Item { Layout.fillWidth: true }

            // DND Toggle Button
            ThemeButton {
                glyph: Notifications.silent ? Icons.bellZ : Icons.bell
                text: "Do not disturb"
                emphasized: Notifications.silent
                Accessible.description: Notifications.silent ? "On" : "Off"
                onClicked: Notifications.toggleSilent()
            }

            // Clear All Button
            ThemeButton {
                visible: root.totalCount > 0
                enabled: !root.isClearing
                glyph: Icons.broom
                text: "Clear all"
                danger: true
                onClicked: root.discardAllWithAnimation()
            }
        }

        Separator { Layout.fillWidth: true; implicitHeight: 1 }

        // ═══════════════════════════════════════════════════════════════
        // NATIVE NOTIFICATIONS LIST (Single unified surface)
        // ═══════════════════════════════════════════════════════════════
        StyledRect {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Styling.radius(2)
            variant: "internalbg"
            clip: true

            // Empty state
            ColumnLayout {
                anchors.centerIn: parent
                spacing: Styling.spacing(8)
                visible: Notifications.appNameList.length === 0

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    renderType: Text.NativeRendering
                    font.hintingPreference: Font.PreferFullHinting
                    text: Icons.bell
                    font.family: Icons.font
                    font.pixelSize: Styling.fontSize(18)
                    color: Colors.overSurfaceVariant
                    opacity: 0.5
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    renderType: Text.NativeRendering
                    font.hintingPreference: Font.PreferFullHinting
                    text: "No notifications"
                    font.family: Config.theme.font
                    font.pixelSize: Styling.fontSize(0)
                    color: Colors.overSurfaceVariant
                }
            }

            // Native scrollable notification list
            ListView {
                id: notificationList
                anchors.fill: parent
                anchors.margins: 8
                spacing: Styling.spacing(6)
                model: Notifications.appNameList
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                visible: Notifications.appNameList.length > 0

                delegate: NotificationGroup {
                    required property int index
                    required property string modelData
                    width: notificationList.width
                    notificationGroup: Notifications.groupsByAppName[modelData]
                    popup: false
                }
            }
        }
    }
}
