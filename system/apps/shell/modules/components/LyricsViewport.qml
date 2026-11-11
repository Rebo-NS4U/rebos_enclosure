pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import qs.modules.services
import qs.modules.theme

Item {
    id: root
    property bool compact: false
    readonly property bool synced: LyricsService.lines.length > 0
    readonly property int activeIndex: LyricsService.currentLine
    readonly property real followPosition: scroller.contentY
    readonly property bool animating: followAnimation.running
    property bool browsing: false

    function followCurrent(animate) {
        if (!synced || browsing || !visible) return;
        const row = rows.itemAt(Math.max(0, activeIndex));
        if (!row) return;
        const destination = Math.max(0, Math.min(scroller.contentHeight - scroller.height,
            row.y + row.height / 2 - scroller.height / 2));
        followAnimation.stop();
        if (animate && Motion.enabled) {
            followAnimation.from = scroller.contentY;
            followAnimation.to = destination;
            followAnimation.start();
        } else scroller.contentY = destination;
    }
    onActiveIndexChanged: Qt.callLater(() => root.followCurrent(true))
    onHeightChanged: Qt.callLater(() => root.followCurrent(false))
    onWidthChanged: Qt.callLater(() => root.followCurrent(false))
    onVisibleChanged: if (visible) Qt.callLater(() => root.followCurrent(false))
    Connections {
        target: LyricsService
        function onLinesChanged() {
            followAnimation.stop();
            root.browsing = false;
            resumeFollow.stop();
            scroller.contentY = 0;
            Qt.callLater(() => root.followCurrent(false));
        }
    }
    Connections {
        target: Motion
        function onEnabledChanged() { if (!Motion.enabled) root.followCurrent(false); }
    }
    NumberAnimation {
        id: followAnimation
        target: scroller
        property: "contentY"
        duration: Motion.enabled ? Math.max(240, Math.round(Motion.enter * 1.4)) : 0
        easing.type: Easing.InOutCubic
    }
    Timer {
        id: resumeFollow
        interval: 4000
        onTriggered: { root.browsing = false; root.followCurrent(true); }
    }
    Flickable {
        id: scroller
        objectName: "lyrics-scroller"
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: root.synced ? lyricColumn.height : plainText.implicitHeight + 24
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds
        onMovementStarted: {
            followAnimation.stop();
            root.browsing = true;
            resumeFollow.stop();
        }
        onMovementEnded: resumeFollow.restart()
        ScrollBar.vertical: ScrollBar {
            policy: root.browsing || !root.synced ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
        }
        Column {
            id: lyricColumn
            visible: root.synced
            width: scroller.width
            spacing: 8
            Item { width: 1; height: root.height / 2 }
            Repeater {
                id: rows
                model: LyricsService.lines
                delegate: Item {
                    id: row
                    required property var modelData
                    required property int index
                    readonly property bool current: root.activeIndex === index
                    objectName: "lyric-row-" + index
                    width: lyricColumn.width
                    height: Math.max(48, lyricText.implicitHeight + 28)
                    onHeightChanged: Qt.callLater(() => root.followCurrent(false))

                    Rectangle {
                        anchors.fill: parent
                        anchors.leftMargin: 4
                        anchors.rightMargin: 4
                        radius: Styling.radius(0)
                        opacity: row.current ? 1 : 0
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0; color: Styling.withOpacity(Colors.primary, 0.23) }
                            GradientStop { position: 1; color: Styling.withOpacity(Colors.primary, 0.06) }
                        }
                        border.width: 1
                        border.color: Styling.withOpacity(Colors.primary, 0.3)
                        Behavior on opacity { NumberAnimation { duration: Motion.enter } }
                    }
                    Rectangle {
                        anchors.left: parent.left
                        anchors.leftMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        width: 3
                        height: row.current ? Math.min(26, parent.height - 16) : 0
                        radius: 1.5
                        color: Colors.primary
                        Behavior on height { NumberAnimation { duration: Motion.enter; easing.type: Easing.OutCubic } }
                    }
                    StyledText {
                        id: lyricText
                        objectName: "lyric-line-" + row.index
                        anchors.centerIn: parent
                        width: Math.max(0, parent.width - 44)
                        text: row.modelData.text || "♪"
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: Styling.fontSize(root.compact ? 3 : 1)
                        font.weight: Font.DemiBold
                        color: row.current ? Colors.primary : Colors.overBackground
                        opacity: row.current ? 1 : (Math.abs(row.index - root.activeIndex) <= 1 ? 0.62 : 0.3)
                        scale: row.current ? 1 : 0.94
                        Behavior on color { ColorAnimation { duration: Motion.enter } }
                        Behavior on opacity { NumberAnimation { duration: Motion.enter } }
                        Behavior on scale { NumberAnimation { duration: Motion.enter; easing.type: Easing.OutCubic } }
                    }
                }
            }
            Item { width: 1; height: root.height / 2 }
        }
        StyledText {
            id: plainText
            objectName: "lyrics-text"
            visible: !root.synced
            x: 16
            y: 12
            width: Math.max(0, scroller.width - 32)
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
            text: LyricsService.plain || LyricsService.status
            horizontalAlignment: Text.AlignHCenter
            lineHeight: 1.4
        }
    }
}
