pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.modules.components
import qs.modules.theme

ColumnLayout {
    id: root
    objectName: "music-daily-mixes"
    property var mixes: ({current: [], saved: [], checked: ""})
    property var localTracks: []
    property string currentPath: ""
    property string notice: ""
    property bool downloadBusy: false
    property var selected: null
    readonly property var previewTracks: selected ? selected.tracks.map(t => ({
        track: t, local: localTracks.find(local => local.spotifyUri === t.uri) || null
    })) : []
    readonly property var playableTracks: previewTracks.filter(row => row.local).map(row => row.local)
    signal playRequested(var list, int index)
    signal downloadRequested(var mix)
    signal requested(string cmd, var args, var callback)
    function refresh() { requested("mixes_get", {}, data => { root.mixes = data; }); }
    onVisibleChanged: if (visible) refresh()
    Timer { interval: 15000; running: root.visible; repeat: true; onTriggered: root.refresh() }
    spacing: 12
    StyledText { text: "Daily Mixes"; font.bold: true; font.pixelSize: Styling.fontSize(10) }
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Colors.overSurfaceVariant
        text: "Keep Spotify and Music open. Open Spotify’s Made for You page once per Spotify session to discover your mixes. Updates are checked every hour. Saved snapshots keep the track list, not audio files."
    }
    StyledText { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: root.notice; visible: text.length > 0; color: Colors.error }
    ThemeButton {
        objectName: "music-mixes-update"
        text: root.mixes.refreshPending ? "Updating Spotify mixes…" : "Update Spotify playlists"
        enabled: !root.mixes.refreshPending
        onClicked: root.requested("mixes_refresh", {}, data => { root.mixes = data; })
    }
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.WordWrap
        text: root.mixes.refreshStatus || ""; visible: text.length > 0
        color: Colors.overSurfaceVariant
    }
    ThemeButton { text: "Open Made for You"; onClicked: Qt.openUrlExternally("spotify:genre:made-for-x-hub") }
    StyledText { text: root.mixes.checked ? "Last received: " + new Date(root.mixes.checked).toLocaleString() : "Waiting for Spotify’s desktop integration…"; color: Colors.overSurfaceVariant }
    ScrollView {
        Layout.fillWidth: true; Layout.preferredHeight: root.selected ? 170 : 300; Layout.fillHeight: !root.selected; contentWidth: availableWidth; clip: true
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
                            ThemeButton { text: "Download"; enabled: !root.downloadBusy; onClicked: { root.selected = mix.modelData; root.downloadRequested(mix.modelData); } }
                            ThemeButton { text: "View tracks"; onClicked: root.selected = mix.modelData }
                            ThemeButton {
                                text: "Save current"; visible: !mix.modelData.savedAt
                                onClicked: root.requested("mixes_save", {uri: mix.modelData.uri, version: mix.modelData.version}, data => { root.mixes = data; })
                            }
                        }
                    }
                }
            }
        }
    }
    RowLayout {
        visible: !!root.selected
        Layout.fillWidth: true
        StyledText {
            Layout.fillWidth: true; elide: Text.ElideRight
            text: root.selected ? root.selected.name + " · " + root.playableTracks.length + "/" + root.previewTracks.length + " downloaded" : ""
            font.bold: true
        }
        ThemeButton { text: "Play downloaded"; enabled: root.playableTracks.length > 0; onClicked: root.playRequested(root.playableTracks, 0) }
        ThemeButton { text: "Close preview"; onClicked: root.selected = null }
    }
    StyledText {
        visible: !!root.selected && root.playableTracks.length === 0
        Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Colors.overSurfaceVariant
        text: "Download this mix to play it here. Choose a format in Downloads, then start."
    }
    ListView {
        id: preview
        objectName: "music-mix-preview"
        visible: !!root.selected
        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6
        model: root.previewTracks
        delegate: ThemeButton {
            required property var modelData
            required property int index
            width: preview.width
            text: (index + 1) + "  " + modelData.track.title + " — " + modelData.track.artist + (modelData.local ? "" : " · Not downloaded")
            enabled: !!modelData.local
            highlighted: !!modelData.local && modelData.local.path === root.currentPath
            onClicked: root.playRequested(root.playableTracks, root.playableTracks.findIndex(t => t.path === modelData.local.path))
        }
        ScrollBar.vertical: ScrollBar {}
    }
}
