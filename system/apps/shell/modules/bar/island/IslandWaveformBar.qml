pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell.Services.Mpris
import qs.modules.services
import qs.modules.theme
import qs.modules.components
import qs.config

Item {
    id: root

    implicitWidth: 400
    implicitHeight: 38

    readonly property real position: MprisController.activePlayer?.position ?? 0.0
    readonly property real length: Math.max(1.0, MprisController.activePlayer?.length ?? 1.0)
    readonly property real progress: Math.min(1.0, Math.max(0.0, root.position / root.length))
    readonly property bool isPlaying: MprisController.isPlaying

    property bool isDragging: false
    property real dragProgress: 0.0
    readonly property real displayProgress: isDragging ? dragProgress : root.progress

    function formatTime(seconds: real): string {
        const totalSecs = Math.max(0, Math.floor(seconds));
        const mins = Math.floor(totalSecs / 60);
        const secs = totalSecs % 60;
        return mins + ":" + (secs < 10 ? "0" : "") + secs;
    }

    Timer {
        running: MprisController.isPlaying && !root.isDragging
        interval: 1000
        repeat: true
        onTriggered: {
            MprisController.activePlayer?.positionChanged();
        }
    }

    function seekTo(fraction: real) {
        if (!MprisController.activePlayer)
            return;
        const player = MprisController.activePlayer;
        const targetPos = Math.max(0.0, Math.min(root.length, fraction * root.length));
        if (player.canSeek ?? true) {
            player.position = targetPos;
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Styling.spacing(4)

        // Shared progress rail with the existing seek interaction.
        Item {
            id: waveformArea
            Layout.fillWidth: true
            Layout.preferredHeight: 20

            MouseArea {
                id: waveMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                preventStealing: root.isDragging

                onPressed: mouse => {
                    root.isDragging = true;
                    root.dragProgress = Math.max(0.0, Math.min(1.0, mouse.x / width));
                }

                onPositionChanged: mouse => {
                    if (root.isDragging) {
                        root.dragProgress = Math.max(0.0, Math.min(1.0, mouse.x / width));
                    }
                }

                onReleased: mouse => {
                    if (root.isDragging) {
                        const finalProgress = Math.max(0.0, Math.min(1.0, mouse.x / width));
                        root.seekTo(finalProgress);
                        root.isDragging = false;
                    }
                }

                onCanceled: {
                    root.isDragging = false;
                }
            }

            StandardProgressBar {
                id: seekProgress
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                value: root.displayProgress
                playing: root.isPlaying
                pressed: root.isDragging
            }

            // Playhead handle: vertical rounded capsule matching reference
            Rectangle {
                id: playheadHandle
                property real handleW: waveMouseArea.containsMouse || root.isDragging ? 5 : 4
                property real handleH: waveMouseArea.containsMouse || root.isDragging ? 18 : 16

                x: Math.max(0, Math.min(waveformArea.width - width, seekProgress.filledLength - width / 2))
                anchors.verticalCenter: parent.verticalCenter
                width: handleW
                height: handleH
                radius: width / 2
                color: Colors.overBackground

                Behavior on width { NumberAnimation { duration: Motion.feedback; easing.type: Easing.OutQuad } }
                Behavior on height { NumberAnimation { duration: Motion.feedback; easing.type: Easing.OutQuad } }
            }
        }

        // Time labels
        RowLayout {
            Layout.fillWidth: true

            Text {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                text: root.formatTime(root.isDragging ? root.dragProgress * root.length : root.position)
                font.family: Config.theme.monoFont
                font.pixelSize: Styling.fontSize(-2)
                color: Colors.overSurfaceVariant
            }

            Item {
                Layout.fillWidth: true
            }

            Text {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                text: root.formatTime(root.length)
                font.family: Config.theme.monoFont
                font.pixelSize: Styling.fontSize(-2)
                color: Colors.overSurfaceVariant
            }
        }
    }
}
