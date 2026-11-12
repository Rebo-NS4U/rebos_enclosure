pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import qs.modules.services
import qs.modules.theme

Item {
    id: root
    property bool compact: false
    readonly property bool synced: LyricsService.lines.length > 0
    readonly property var plainRows: LyricsService.plain.split(/\r?\n/)
        .map(text => ({text: text.trim()})).filter(row => row.text.length > 0)
    readonly property bool hasRows: synced || plainRows.length > 0
    readonly property int activeIndex: LyricsService.currentLine
    readonly property int followIndex: LyricsService.followLine
    readonly property real followPosition: scroller.contentY
    readonly property bool animating: followAnimation.running
    property bool browsing: false

    function resume() {
        browsing = false;
        scroller.cancelFlick();
        followCurrent(true);
    }

    function followCurrent(animate) {
        if (!synced || browsing || !visible) return;
        const row = rows.itemAt(Math.max(0, followIndex));
        if (!row) return;
        const destination = Math.max(0, Math.min(scroller.contentHeight - scroller.height,
            row.y + row.height / 2 - scroller.height / 2));
        if (animate && Motion.enabled) {
            // Retarget without discarding velocity when cues arrive close together.
            followAnimation.destination = destination;
            followAnimation.running = true;
        } else {
            followAnimation.running = false;
            followAnimation.velocity = 0;
            scroller.contentY = destination;
        }
    }
    onFollowIndexChanged: Qt.callLater(() => root.followCurrent(true))
    onHeightChanged: Qt.callLater(() => root.followCurrent(false))
    onWidthChanged: Qt.callLater(() => root.followCurrent(false))
    onVisibleChanged: {
        if (visible) Qt.callLater(() => root.followCurrent(false));
        else followAnimation.running = false;
    }
    onBrowsingChanged: if (browsing) { followAnimation.running = false; followAnimation.velocity = 0; }
    Connections {
        target: LyricsService
        function onLinesChanged() {
            followAnimation.running = false;
            followAnimation.velocity = 0;
            root.browsing = false;
            scroller.contentY = 0;
            Qt.callLater(() => root.followCurrent(false));
        }
    }
    Connections {
        target: Motion
        function onEnabledChanged() { if (!Motion.enabled) root.followCurrent(false); }
    }
    FrameAnimation {
        id: followAnimation
        property real destination: 0
        property real velocity: 0
        onTriggered: {
            // Exact critically damped spring step: stable even after a slow frame.
            const dt = Math.min(0.1, Math.max(0, frameTime));
            const omega = 10000 / 650;
            const offset = scroller.contentY - destination;
            const step = velocity + omega * offset;
            const decay = Math.exp(-omega * dt);
            velocity = (velocity - omega * step * dt) * decay;
            scroller.contentY = destination + (offset + step * dt) * decay;
            if (Math.abs(scroller.contentY - destination) < 0.5 && Math.abs(velocity) < 10) {
                scroller.contentY = destination;
                velocity = 0;
                running = false;
            }
        }
    }
    Flickable {
        id: scroller
        objectName: "lyrics-scroller"
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: root.hasRows ? lyricColumn.height : statusText.implicitHeight + 24
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds
        onMovementStarted: {
            root.browsing = true;
        }
        ScrollBar.vertical: ScrollBar {
            policy: root.browsing || !root.synced ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
            onPressedChanged: if (pressed) root.browsing = true
        }
        Column {
            id: lyricColumn
            visible: root.hasRows
            width: scroller.width
            spacing: root.synced ? 8 : 12
            Item { width: 1; height: root.synced ? root.height / 2 : 8 }
            Repeater {
                id: rows
                model: root.synced ? LyricsService.lines : root.plainRows
                delegate: Item {
                    id: row
                    required property var modelData
                    required property int index
                    readonly property bool current: root.synced && root.activeIndex === index
                    readonly property bool emphasized: current || (!root.synced && rowHover.hovered)
                    objectName: "lyric-row-" + index
                    width: lyricColumn.width
                    height: Math.max(48, lyricText.implicitHeight + 28)
                    onHeightChanged: Qt.callLater(() => root.followCurrent(false))

                    HoverHandler { id: rowHover }
                    Rectangle {
                        anchors.fill: parent
                        anchors.leftMargin: 4
                        anchors.rightMargin: 4
                        radius: Styling.radius(0)
                        opacity: row.emphasized ? 1 : (root.synced ? 0 : 0.18)
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
                        height: row.emphasized ? Math.min(26, parent.height - 16) : 0
                        radius: 1.5
                        color: Colors.primary
                        Behavior on height { NumberAnimation { duration: Motion.enter; easing.type: Easing.OutCubic } }
                    }
                    StyledText {
                        id: lyricText
                        objectName: !root.synced && row.index === 0 ? "lyrics-text" : "lyric-line-" + row.index
                        anchors.centerIn: parent
                        width: Math.max(0, parent.width - 44)
                        text: row.modelData.text || "♪"
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: Styling.fontSize(root.compact ? 3 : 1)
                        font.weight: Font.DemiBold
                        color: row.emphasized ? Colors.primary : Colors.overBackground
                        opacity: !root.synced ? 0.9 : (row.current ? 1 : (Math.abs(row.index - root.activeIndex) <= 1 ? 0.62 : 0.3))
                        scale: row.emphasized || !root.synced ? 1 : 0.94
                        Behavior on color { ColorAnimation { duration: Motion.enter } }
                        Behavior on opacity { NumberAnimation { duration: Motion.enter } }
                        Behavior on scale { NumberAnimation { duration: Motion.enter; easing.type: Easing.OutCubic } }
                    }
                }
            }
            Item { width: 1; height: root.synced ? root.height / 2 : 8 }
        }
        StyledText {
            id: statusText
            objectName: "lyrics-status"
            visible: !root.hasRows
            x: 16
            y: 12
            width: Math.max(0, scroller.width - 32)
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
            text: LyricsService.status
            horizontalAlignment: Text.AlignHCenter
            lineHeight: 1.4
        }
    }
    ThemeButton {
        objectName: "lyrics-follow-playback"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        visible: root.synced && root.browsing
        text: "Follow playback"
        onClicked: root.resume()
    }
}
