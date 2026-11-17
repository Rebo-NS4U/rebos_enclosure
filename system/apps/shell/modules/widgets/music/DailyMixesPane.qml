pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.modules.components
import qs.modules.theme

ColumnLayout {
    id: root
    property var mixes: ({current: [], saved: [], checked: ""})
    property var selected: null
    signal requested(string cmd, var args, var callback)
    function refresh() { requested("mixes_get", {}, data => { root.mixes = data; }); }
    onVisibleChanged: if (visible) refresh()
    Timer { interval: 15000; running: root.visible; repeat: true; onTriggered: root.refresh() }
    spacing: 12
    StyledText { text: "Daily Mixes"; font.bold: true; font.pixelSize: Styling.fontSize(10) }
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Colors.overSurfaceVariant
        text: "Keep Spotify and Music open. Open Spotify’s Made for You page once per Spotify session to discover your mixes. Updates are checked every 15 minutes. Saved snapshots keep the track list, not audio files."
    }
    ThemeButton { text: "Open Made for You"; onClicked: Qt.openUrlExternally("spotify:genre:made-for-x-hub") }
    StyledText { text: root.mixes.checked ? "Last received: " + new Date(root.mixes.checked).toLocaleString() : "Waiting for Spotify’s desktop integration…"; color: Colors.overSurfaceVariant }
    ScrollView {
        Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth; clip: true
        ColumnLayout {
            width: parent.width; spacing: 10
            Repeater {
                model: [{title: "Current mixes", rows: root.mixes.current}, {title: "Saved snapshots", rows: root.mixes.saved}]
                delegate: ColumnLayout {
                    id: section
                    required property var modelData
                    Layout.fillWidth: true
                    StyledText { text: section.modelData.title; font.bold: true }
                    Repeater {
                        model: section.modelData.rows
                        delegate: RowLayout {
                            id: mix
                            required property var modelData
                            Layout.fillWidth: true
                            StyledText { Layout.fillWidth: true; text: mix.modelData.name + " · " + mix.modelData.tracks.length + " songs" + (mix.modelData.savedAt ? " · " + new Date(mix.modelData.savedAt).toLocaleString() : "") }
                            ThemeButton { text: "View tracks"; onClicked: root.selected = mix.modelData }
                            ThemeButton {
                                text: "Save current"; visible: !mix.modelData.savedAt
                                onClicked: root.requested("mixes_save", {uri: mix.modelData.uri, version: mix.modelData.version}, data => { root.mixes = data; })
                            }
                        }
                    }
                }
            }
            StyledText { visible: !!root.selected; text: root.selected ? root.selected.name : ""; font.bold: true }
            Repeater {
                model: root.selected ? root.selected.tracks : []
                delegate: ThemeButton {
                    required property var modelData
                    Layout.fillWidth: true
                    text: modelData.title + " — " + modelData.artist
                    onClicked: Qt.openUrlExternally(modelData.uri)
                }
            }
        }
    }
}
