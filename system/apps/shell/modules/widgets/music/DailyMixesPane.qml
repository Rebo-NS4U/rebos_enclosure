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
    property var importedPlaylists: []
    property bool previewOnly: false
    readonly property var importedSources: importedPlaylists.map(playlist => ({
        uri: playlist.id, name: playlist.name, imported: true,
        tracks: (playlist.paths || []).map(path => localTracks.find(track => track.path === path))
            .filter(Boolean).map(track => ({path: track.path, uri: track.spotifyUri || "",
                title: track.title, artist: track.artist}))
    }))
    property string currentPath: ""
    property string notice: ""
    property string previewStatus: ""
    property bool downloadBusy: false
    property var selected: null
    property var lastPreviewByMix: ({})
    property string section: "current"
    readonly property bool wide: width >= Styling.spacing(940)
    readonly property var displayedMixes: section === "imported" ? importedSources : mixes[section] || []
    readonly property var previewTracks: selected ? selected.tracks.map(t => ({
        track: t, local: localTracks.find(local => (t.path && local.path === t.path) || (t.uri && local.spotifyUri === t.uri)) || null
    })) : []
    readonly property var playableTracks: previewTracks.filter(row => row.local).map(row => row.local)
    signal playRequested(var list, int index)
    signal previewRequested(string uri)
    signal downloadRequested(var mix)
    signal requested(string cmd, var args, var callback)
    function canPreview(mix, track) {
        return (mix.imported && !!track.path && localTracks.some(local => local.path === track.path))
            || /^spotify:track:[A-Za-z0-9]{22}$/.test(track.uri || "");
    }
    function previewRandomMix(mix) {
        const tracks = (mix?.tracks || []).filter(track => canPreview(mix, track));
        if (!tracks.length) return false;
        const key = (mix.uri || mix.name || "") + ":" + (mix.version || mix.savedAt || "");
        const previous = lastPreviewByMix[key];
        const alternatives = tracks.filter(track => (track.path || track.uri) !== previous);
        const choices = alternatives.length ? alternatives : tracks;
        const track = choices[Math.floor(Math.random() * choices.length)];
        lastPreviewByMix = Object.assign({}, lastPreviewByMix, {[key]: track.path || track.uri});
        if (mix.imported && track.path && localTracks.some(local => local.path === track.path)) {
            const local = tracks.map(t => localTracks.find(item => item.path === t.path)).filter(Boolean);
            previewStatus = "Previewing from your library · " + track.title;
            playRequested(local, local.findIndex(item => item.path === track.path));
        } else {
            previewStatus = "Opening a random song in Spotify · " + track.title;
            previewRequested(track.uri);
        }
        return true;
    }
    function loadPlaylist() {
        if (!playlistLink.text.trim() || mixes.refreshPending) return;
        previewStatus = "";
        requested("mixes_load", {link: playlistLink.text.trim()}, data => {
            root.mixes = data;
            root.section = "current";
        });
    }
    function refresh() { requested("mixes_get", {}, data => { root.mixes = data; }); }
    onVisibleChanged: if (visible) refresh()
    onPreviewOnlyChanged: { section = previewOnly ? "imported" : "current"; selected = null; }
    onSelectedChanged: { previewStatus = ""; preview.currentIndex = -1; preview.positionViewAtBeginning(); }
    Timer { interval: 15000; running: root.visible; repeat: true; onTriggered: root.refresh() }

    ColumnLayout {
        anchors.fill: parent
        spacing: Styling.spacing(10)
        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(8)
            StyledText { Layout.fillWidth: true; text: root.previewOnly ? "Previews" : "Spotify playlists"; font.bold: true; font.pixelSize: Styling.fontSize(14) }
            ThemeButton { objectName: "music-preview-mode"; text: root.previewOnly ? "Browse playlists" : "Previews"; checked: root.previewOnly; onClicked: root.previewOnly = !root.previewOnly }
            ThemeButton {
                objectName: "music-mixes-update"
                visible: !root.previewOnly
                text: root.mixes.refreshPending ? "Updating…" : "Update mixes"
                enabled: !root.mixes.refreshPending
                onClicked: root.requested("mixes_refresh", {}, data => { root.mixes = data; })
            }
            ThemeButton { visible: !root.previewOnly; text: "Made for You ↗"; Accessible.name: "Open Made for You in Spotify"; onClicked: Qt.openUrlExternally("spotify:genre:made-for-x-hub") }
        }
        RowLayout {
            visible: !root.previewOnly
            Layout.fillWidth: true
            SearchInput {
                id: playlistLink
                objectName: "music-playlist-link"
                Layout.fillWidth: true
                placeholderText: "Paste a Spotify playlist link"
                onAccepted: root.loadPlaylist()
            }
            ThemeButton {
                objectName: "music-playlist-load"
                text: root.mixes.refreshPending ? "Loading…" : "Load playlist"
                enabled: playlistLink.text.trim() !== "" && !root.mixes.refreshPending
                onClicked: root.loadPlaylist()
            }
        }
        StyledText {
            Layout.fillWidth: true; wrapMode: Text.WordWrap
            text: {
                if (root.notice) return root.notice;
                if (root.previewOnly) return root.previewStatus || "Choose an imported playlist or Spotify list, then preview a random song or view its tracks.";
                if (root.mixes.refreshPending) return "Waiting for Spotify…";
                return root.previewStatus || root.mixes.refreshStatus || (root.mixes.checked
                    ? "Updated " + new Date(root.mixes.checked).toLocaleString() + " · Preview streams in Spotify; downloads are optional."
                    : "Load a playlist by link, or open Made for You in Spotify and choose Update mixes.");
            }
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
                    ThemeButton { objectName: "music-previews-imported"; visible: root.previewOnly; text: "Imported · " + root.importedSources.length; checked: root.section === "imported"; onClicked: { root.section = "imported"; root.selected = null; } }
                    ThemeButton { objectName: "music-mixes-current"; text: (root.previewOnly ? "Spotify · " : "Current · ") + (root.mixes.current || []).length; checked: root.section === "current"; onClicked: root.section = "current" }
                    ThemeButton { objectName: "music-mixes-saved"; text: "Saved · " + (root.mixes.saved || []).length; checked: root.section === "saved"; onClicked: root.section = "saved" }
                }
                GridView {
                    id: mixGrid
                    objectName: "music-mix-grid"
                    Layout.fillWidth: true; Layout.fillHeight: true
                    clip: true
                    cellWidth: width / Math.max(1, Math.floor(width / Styling.spacing(270)))
                    cellHeight: Styling.spacing(210)
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
                            border.width: !!root.selected && root.selected.version === mix.modelData.version && root.selected.uri === mix.modelData.uri ? 2 : 1
                            border.color: !!root.selected && root.selected.version === mix.modelData.version && root.selected.uri === mix.modelData.uri ? Colors.primary : Qt.alpha(Colors.outline, 0.3)
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
                                    text: mix.modelData.tracks.length + " songs" + (mix.modelData.savedAt ? " · " + new Date(mix.modelData.savedAt).toLocaleDateString() : (mix.modelData.imported ? " · Imported" : " · Spotify"))
                                    color: Colors.overSurfaceVariant; elide: Text.ElideRight
                                    font.pixelSize: Styling.fontSize(-1)
                                }
                                Item { Layout.fillHeight: true }
                                Flow {
                                    Layout.fillWidth: true; spacing: Styling.spacing(4)
                                    ThemeButton {
                                        objectName: "music-mix-stream-preview-" + mix.index
                                        text: "Preview random"
                                        Accessible.name: "Preview a random song from " + mix.modelData.name
                                        highlighted: true
                                        enabled: mix.modelData.tracks.some(track => root.canPreview(mix.modelData, track))
                                        onClicked: root.previewRandomMix(mix.modelData)
                                    }
                                    ThemeButton { objectName: "music-mix-view-" + mix.index; text: "View tracks"; onClicked: root.selected = mix.modelData }
                                    ThemeButton { visible: !root.previewOnly && !mix.modelData.imported; text: "Download"; enabled: !root.downloadBusy; onClicked: { root.selected = mix.modelData; root.downloadRequested(mix.modelData); } }
                                    ThemeButton {
                                        text: "Save"; Accessible.name: "Save mix snapshot"; visible: !root.previewOnly && !mix.modelData.imported && !mix.modelData.savedAt
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
                        text: root.section === "imported" ? "No imported playlists yet. Add music folders or save a playlist from the queue." : root.section === "saved" ? "No saved snapshots yet. Save a current mix to keep its track list." : "No Spotify playlists loaded yet."
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
                        ThemeButton { objectName: "music-previews-next"; visible: root.previewOnly; text: "Next preview"; enabled: !!root.selected && root.selected.tracks.some(track => root.canPreview(root.selected, track)); onClicked: root.previewRandomMix(root.selected) }
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
                            enabled: !!modelData.local || !!modelData.track.uri
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
