pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.components
import qs.modules.theme

Item {
    id: root
    objectName: "music-daily-mixes"
    property var mixes: ({current: [], saved: [], checked: ""})
    property var localTracks: []
    property string currentPath: ""
    property string notice: ""
    property string previewStatus: ""
    property bool downloadBusy: false
    property var selected: null
    property string section: "current"
    readonly property bool wide: width >= Styling.spacing(940)
    readonly property var displayedMixes: mixes[section] || []
    readonly property var previewTracks: selected ? selected.tracks.map(t => ({
        track: t, local: localTracks.find(local => local.spotifyUri === t.uri) || null
    })) : []
    readonly property var playableTracks: previewTracks.filter(row => row.local).map(row => row.local)
    signal playRequested(var list, int index)
    signal previewRequested(string uri)
    signal downloadRequested(var mix)
    signal requested(string cmd, var args, var callback)
    function refresh() { requested("mixes_get", {}, data => { root.mixes = data; }); }
    onVisibleChanged: if (visible) refresh()
    onSelectedChanged: { previewStatus = ""; preview.currentIndex = -1; preview.positionViewAtBeginning(); }
    Timer { interval: 15000; running: root.visible; repeat: true; onTriggered: root.refresh() }

    ColumnLayout {
        anchors.fill: parent
        spacing: Styling.spacing(10)
        Flow {
            Layout.fillWidth: true
            spacing: Styling.spacing(8)
            StyledText { text: "Daily Mixes"; font.bold: true; font.pixelSize: Styling.fontSize(8); height: Math.max(36, Styling.spacing(40)); verticalAlignment: Text.AlignVCenter }
            ThemeButton {
                objectName: "music-mixes-update"
                text: root.mixes.refreshPending ? "Updating…" : "Update mixes"
                enabled: !root.mixes.refreshPending
                onClicked: root.requested("mixes_refresh", {}, data => { root.mixes = data; })
            }
            ThemeButton { text: "Made for You ↗"; Accessible.name: "Open Made for You in Spotify"; onClicked: Qt.openUrlExternally("spotify:genre:made-for-x-hub") }
        }
        StyledText {
            Layout.fillWidth: true; wrapMode: Text.WordWrap
            text: root.notice || root.mixes.refreshStatus || (root.mixes.checked
                ? "Updated " + new Date(root.mixes.checked).toLocaleString() + " · Preview streams in Spotify; downloads are optional."
                : "Open Spotify’s Made for You once to discover mixes. Preview streams without a library download.")
            color: root.notice ? Colors.error : Colors.overSurfaceVariant
            font.pixelSize: Styling.fontSize(-1)
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: Styling.spacing(12)
            ColumnLayout {
                visible: root.wide || !root.selected
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.preferredWidth: root.wide && root.selected ? root.width * 0.4 : root.width
                spacing: Styling.spacing(8)
                Flow {
                    Layout.fillWidth: true; spacing: Styling.spacing(6)
                    ThemeButton { objectName: "music-mixes-current"; text: "Current · " + (root.mixes.current || []).length; checked: root.section === "current"; onClicked: root.section = "current" }
                    ThemeButton { objectName: "music-mixes-saved"; text: "Saved · " + (root.mixes.saved || []).length; checked: root.section === "saved"; onClicked: root.section = "saved" }
                }
                GridView {
                    id: mixGrid
                    objectName: "music-mix-grid"
                    Layout.fillWidth: true; Layout.fillHeight: true
                    clip: true
                    cellWidth: width / Math.max(1, Math.floor(width / Styling.spacing(270)))
                    cellHeight: Styling.spacing(182)
                    model: root.displayedMixes
                    boundsBehavior: Flickable.StopAtBounds
                    delegate: Item {
                        id: mix
                        required property var modelData
                        required property int index
                        width: mixGrid.cellWidth; height: mixGrid.cellHeight
                        StyledRect {
                            anchors.fill: parent; anchors.rightMargin: Styling.spacing(8); anchors.bottomMargin: Styling.spacing(8)
                            variant: "pane"
                            border.width: root.selected?.version === mix.modelData.version && root.selected?.uri === mix.modelData.uri ? 2 : 1
                            border.color: root.selected?.version === mix.modelData.version && root.selected?.uri === mix.modelData.uri ? Colors.primary : Qt.alpha(Colors.outline, 0.3)
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: Styling.spacing(12)
                                spacing: Styling.spacing(6)
                                StyledText {
                                    objectName: "music-mix-label"
                                    Layout.fillWidth: true
                                    text: mix.modelData.name
                                    font.bold: true; font.pixelSize: Styling.fontSize(1)
                                    wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight
                                }
                                StyledText {
                                    Layout.fillWidth: true
                                    text: mix.modelData.tracks.length + " songs" + (mix.modelData.savedAt ? " · " + new Date(mix.modelData.savedAt).toLocaleDateString() : " · Live mix")
                                    color: Colors.overSurfaceVariant; elide: Text.ElideRight
                                    font.pixelSize: Styling.fontSize(-1)
                                }
                                Item { Layout.fillHeight: true }
                                Flow {
                                    Layout.fillWidth: true; spacing: Styling.spacing(4)
                                    ThemeButton { objectName: "music-mix-view-" + mix.index; text: "View tracks"; highlighted: true; onClicked: root.selected = mix.modelData }
                                    ThemeButton { text: "Download"; enabled: !root.downloadBusy; onClicked: { root.selected = mix.modelData; root.downloadRequested(mix.modelData); } }
                                    ThemeButton {
                                        text: "Save"; Accessible.name: "Save mix snapshot"; visible: !mix.modelData.savedAt
                                        onClicked: root.requested("mixes_save", {uri: mix.modelData.uri, version: mix.modelData.version}, data => { root.mixes = data; })
                                    }
                                }
                            }
                        }
                    }
                    ScrollBar.vertical: ScrollBar {}
                    StyledText {
                        anchors.centerIn: parent; width: parent.width - Styling.spacing(32)
                        horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
                        visible: mixGrid.count === 0
                        text: root.section === "saved" ? "No saved snapshots yet. Save a current mix to keep its track list." : "No mixes received yet. Open Made for You in Spotify, then update mixes."
                        color: Colors.overSurfaceVariant
                    }
                }
            }
            StyledRect {
                id: previewCard
                objectName: "music-mix-preview-card"
                visible: !!root.selected
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.preferredWidth: root.wide ? root.width * 0.6 : root.width
                variant: "pane"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: Styling.spacing(12)
                    spacing: Styling.spacing(8)
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText {
                            Layout.fillWidth: true
                            text: root.selected?.name || ""
                            font.bold: true; font.pixelSize: Styling.fontSize(2)
                            elide: Text.ElideRight
                        }
                        ThemeButton { text: root.wide ? "Close" : "← Mixes"; onClicked: root.selected = null }
                    }
                    Flow {
                        Layout.fillWidth: true; spacing: Styling.spacing(6)
                        ThemeButton {
                            objectName: "music-mix-stream-preview"
                            text: "Preview in Spotify"
                            highlighted: true; enabled: root.previewTracks.length > 0
                            onClicked: root.previewRequested(root.previewTracks[0].track.uri)
                        }
                        ThemeButton { text: "Play local · " + root.playableTracks.length; enabled: root.playableTracks.length > 0; onClicked: root.playRequested(root.playableTracks, 0) }
                    }
                    StyledText {
                        Layout.fillWidth: true; wrapMode: Text.WordWrap
                        text: root.previewStatus || root.previewTracks.length + " tracks · " + root.playableTracks.length + " local · Click any song to listen."
                        color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-1)
                    }
                    ListView {
                        id: preview
                        objectName: "music-mix-preview"
                        Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true; spacing: Styling.spacing(4)
                        model: root.previewTracks
                        boundsBehavior: Flickable.StopAtBounds
                        delegate: ThemeButton {
                            id: trackRow
                            required property var modelData
                            required property int index
                            width: preview.width
                            implicitHeight: Math.max(Styling.spacing(60), trackContent.implicitHeight + Styling.spacing(16))
                            enabled: !!modelData.track.uri
                            highlighted: !!modelData.local && modelData.local.path === root.currentPath
                            objectName: "music-mix-track-" + index
                            Accessible.name: (modelData.local ? "Play local track: " : "Preview in Spotify: ") + modelData.track.title
                            onActiveFocusChanged: if (activeFocus) preview.positionViewAtIndex(index, ListView.Contain)
                            onClicked: {
                                if (modelData.local) root.playRequested(root.playableTracks, root.playableTracks.findIndex(t => t.path === modelData.local.path));
                                else root.previewRequested(modelData.track.uri);
                            }
                            contentItem: RowLayout {
                                id: trackContent
                                spacing: Styling.spacing(10)
                                StyledText { text: (trackRow.index + 1).toString(); color: trackRow.background.itemColor; font.pixelSize: Styling.fontSize(-1) }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: Styling.spacing(2)
                                    StyledText { Layout.fillWidth: true; text: trackRow.modelData.track.title; color: trackRow.background.itemColor; elide: Text.ElideRight; font.bold: true }
                                    StyledText { Layout.fillWidth: true; text: (trackRow.modelData.track.artist || "Unknown artist") + (trackRow.modelData.local ? " · Local" : " · Spotify preview"); color: trackRow.background.itemColor; elide: Text.ElideRight; font.pixelSize: Styling.fontSize(-2) }
                                }
                                StyledText { text: "▶"; color: trackRow.background.itemColor }
                            }
                        }
                        ScrollBar.vertical: ScrollBar {}
                    }
                }
            }
        }
    }
}
