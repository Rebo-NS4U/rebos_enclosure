pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import Quickshell
import Quickshell.Io
import Quickshell.Services.Mpris
import Quickshell.Widgets
import qs.config
import qs.modules.theme
import qs.modules.components
import qs.modules.globals
import "../../services/Lyrics.js" as Lyrics

Window {
    id: root
    title: "Enclosure Music" // Local library; uses the shell theme.
    width: 1240; height: 800
    minimumWidth: 860; minimumHeight: 600
    // Let the shared bg surface and compositor blur remain visible.
    color: "transparent"
    visible: GlobalStates.musicWindowVisible
    onClosing: event => { event.accepted = false; GlobalStates.musicWindowVisible = false; }
    onVisibleChanged: if (visible && !started) { started = true; backend.running = true; }

    readonly property bool immersive: visibility === Window.FullScreen
    property bool restoreMaximized: false
    function toggleFullscreen() {
        if (immersive) {
            if (restoreMaximized) showMaximized(); else showNormal();
        } else {
            restoreMaximized = visibility === Window.Maximized;
            showFullScreen();
        }
    }
    property bool started: false
    property bool busy: false
    property string notice: ""
    property string lyricText: ""
    property string lyricStatus: "Choose a song to see lyrics."
    property int lyricRequest: 0
    property var tracks: []
    property var favorites: []
    property var playlists: []
    property var folders: []
    property string page: "Albums"
    property string query: ""
    property string detail: ""
    property string side: "Queue"
    readonly property int queueLimit: 100
    property var queue: []
    property int currentIndex: -1
    property bool shuffle: false
    property string repeatMode: "Playlist"
    property real volume: 0.8
    property int requestId: 0
    property var callbacks: ({})
    property bool spotifyPreview: false
    property var spotifyPlayer: Mpris.players.values.find(p => p.dbusName === "org.mpris.MediaPlayer2.spotify") || null
    readonly property var localCurrent: currentIndex >= 0 && currentIndex < queue.length ? queue[currentIndex] : null
    readonly property var current: spotifyPreview ? (spotifyPlayer ? {
        title: spotifyPlayer.trackTitle, artist: spotifyPlayer.trackArtists,
        album: spotifyPlayer.trackAlbum, art: spotifyPlayer.trackArtUrl,
        duration: spotifyPlayer.length, spotifyUri: spotifyPlayer.metadata["xesam:url"] || ""
    } : null) : localCurrent
    readonly property real playbackPosition: spotifyPreview ? (spotifyPlayer?.position || 0) * 1000 : player.position
    readonly property real playbackDuration: spotifyPreview ? (spotifyPlayer?.length || 0) * 1000 : player.duration
    onSpotifyPlayerChanged: if (spotifyPreview) Qt.callLater(findLyrics)
    function previewTrack(uri) {
        request("mixes_preview", {uri: uri}, data => {
            player.pause();
            spotifyPreview = true;
            findLyrics();
        });
    }
    Connections {
        target: root.spotifyPreview ? root.spotifyPlayer : null
        function onTrackTitleChanged() { Qt.callLater(root.findLyrics); }
    }
    Timer {
        interval: 250; repeat: true
        running: root.spotifyPreview && root.playing && root.visible
        onTriggered: if (root.spotifyPlayer) root.spotifyPlayer.positionChanged()
    }
    readonly property bool playing: spotifyPreview ? !!spotifyPlayer?.isPlaying : player.playbackState === MediaPlayer.PlayingState
    readonly property var shownTracks: {
        let list = tracks;
        if (page === "Favorites") list = list.filter(t => favorites.indexOf(t.path) >= 0);
        if (page === "Album") list = list.filter(t => t.album + "\n" + t.artist === detail).slice().sort((a,b) => a.number - b.number);
        if (page === "Artist") list = list.filter(t => t.artist === detail);
        if (page === "Playlist") {
            const pl = playlists.find(p => p.id === detail);
            list = pl ? pl.paths.map(p => tracks.find(t => t.path === p)).filter(Boolean) : [];
        }
        const q = query.trim().toLowerCase();
        return q ? list.filter(t => (t.title + " " + t.artist + " " + t.album).toLowerCase().includes(q)) : list;
    }
    property var spotifySuggestions: ({tracks: [], pending: false, status: ""})
    property var pendingSuggestionDownload: null
    readonly property var suggestedTracks: {
        const playlist = playlists.find(p => p.id === detail);
        if (page !== "Playlist" || !playlist || spotifySuggestions.playlist !== detail) return [];
        const members = tracks.filter(t => playlist.paths.includes(t.path));
        const identities = new Set(members.map(t => (t.artist + "\n" + t.title).toLowerCase()));
        const uris = new Set(members.map(t => t.spotifyUri));
        return (spotifySuggestions.tracks || []).filter(t => {
            const key = (t.artist + "\n" + t.title).toLowerCase();
            if (uris.has(t.uri) || identities.has(key)) return false;
            uris.add(t.uri); identities.add(key); return true;
        }).slice(0, 100);
    }
    function refreshSuggestions() {
        if (page !== "Playlist") return;
        const selected = detail;
        spotifySuggestions = {playlist: selected, tracks: [], pending: true, status: "Loading Spotify suggestions…"};
        request("suggestions_refresh", {playlist: selected}, data => {
            if (detail === selected) spotifySuggestions = data;
        });
    }
    Timer {
        interval: 2000; repeat: true
        running: root.page === "Playlist" && root.spotifySuggestions.pending
        onTriggered: root.request("suggestions_get", {}, data => {
            if (data.playlist === root.detail) root.spotifySuggestions = data;
        })
    }
    readonly property var albums: {
        const result = {};
        shownTracks.forEach(t => { const key = t.album + "\n" + t.artist;
            if (!result[key]) result[key] = { key: key, title: t.album, subtitle: t.artist, art: t.art, count: 0 };
            result[key].count++;
        });
        return Object.values(result);
    }
    readonly property var artists: {
        const result = {};
        shownTracks.forEach(t => {
            if (!result[t.artist]) result[t.artist] = { key: t.artist, title: t.artist, subtitle: "Artist", art: t.art, count: 0 };
            result[t.artist].count++;
        });
        return Object.values(result);
    }
    readonly property string pageTitle: page === "Album" ? detail.split("\n")[0] : page === "Artist" ? detail : page === "Playlist" ? (playlists.find(p => p.id === detail)?.name || "Playlist") : page
    readonly property bool estimatedTiming: lyricText.trim().length > 0 && Lyrics.parseLrc(lyricText).length === 0
    readonly property var lyricLines: {
        const raw = lyricText;
        if (estimatedTiming) return Lyrics.estimatedLines(raw, playbackDuration > 0 ? playbackDuration/1000 : (current?.duration || 0));
        let result = [];
        raw.split("\n").forEach(line => {
            const stamps = [];
            const pattern = /\[(\d+):(\d+(?:\.\d+)?)\]/g;
            let stamp;
            while ((stamp = pattern.exec(line)) !== null) stamps.push(stamp);
            const text = line.replace(/\[[^\]]*\]/g, "").trim();
            if (text) {
                if (stamps.length) stamps.forEach(m => result.push({time: Number(m[1])*60+Number(m[2]), text: text}));
                else result.push({time: -1, text: text});
            }
        });
        return result.sort((a,b) => a.time-b.time);
    }
    readonly property int lyricIndex: {
        let found = -1;
        for (let i = 0; i < lyricLines.length; i++) if (lyricLines[i].time >= 0 && lyricLines[i].time <= playbackPosition/1000) found = i;
        return found;
    }
    onLyricIndexChanged: if (lyricIndex >= 0) {
        lyricsList.positionViewAtIndex(lyricIndex, ListView.Center);
        fullscreenLyrics.positionViewAtIndex(lyricIndex, ListView.Center);
    }

    function time(ms) { const s = Math.max(0, Math.floor(ms/1000)); return Math.floor(s/60) + ":" + (s%60 < 10 ? "0" : "") + s%60; }
    function request(cmd, args, callback) {
        const id = ++requestId;
        if (callback) callbacks[id] = callback;
        backend.write(JSON.stringify({id: id, cmd: cmd, args: args || {}}) + "\n");
    }
    function receive(data) {
        let message;
        try { message = JSON.parse(data); } catch (e) { return; }
        if (message.event === "control") { control(message); return; }
        const callback = callbacks[message.id];
        delete callbacks[message.id];
        if (!message.ok) { busy = false; notice = message.error; if (spotifySuggestions.pending) spotifySuggestions = Object.assign({}, spotifySuggestions, {pending:false}); return; }
        if (callback) callback(message.data);
    }
    function load(data) {
        busy = false;
        if (!data) return;
        tracks = data.tracks; favorites = data.state.favorites; playlists = data.state.playlists; folders = data.state.folders;
        notice = data.errors.length ? data.errors.length + " files could not be read" : "";
    }
    function scan() { if (busy) return; busy = true; request("scan", {}, load); }
    function save() { request("save", { favorites: favorites, playlists: playlists }); }
    function favorite(track) {
        if (!track?.path) return;
        favorites = favorites.includes(track.path) ? favorites.filter(p => p !== track.path) : favorites.concat([track.path]); save();
    }
    function navigate(value, arg) { page = value; detail = arg || ""; query = ""; if (page === "Playlist") refreshSuggestions(); }
    function play(list, index) {
        if (!list.length) return;
        const selected = index === undefined ? Math.floor(Math.random() * list.length) : index;
        if (selected < 0 || selected >= list.length) return;
        const start = selected >= queueLimit ? Math.min(selected, Math.max(0, list.length - queueLimit)) : 0;
        queue = list.slice(start, start + queueLimit);
        notice = list.length > queueLimit ? "Queue limited to " + queueLimit + " songs." : "";
        select(selected - start);
    }
    function enqueue(track) {
        if (queue.length >= queueLimit) {
            notice = "Queue is full (" + queueLimit + " songs).";
            return;
        }
        queue = queue.concat([track]);
    }
    function cardTracks(kind, key) {
        if (kind === "Playlists") {
            const playlist = playlists.find(p => p.id === key);
            return playlist ? playlist.paths.map(path => tracks.find(t => t.path === path)).filter(Boolean) : [];
        }
        if (kind === "Artists") return tracks.filter(t => t.artist === key);
        return tracks.filter(t => t.album + "\n" + t.artist === key).slice().sort((a,b) => a.number - b.number);
    }
    function select(index) {
        if (index < 0 || index >= queue.length) return;
        if (spotifyPreview && spotifyPlayer?.isPlaying) spotifyPlayer.pause();
        spotifyPreview = false;
        currentIndex = index;
        findLyrics();
        player.source = queue[index].url;
        player.play();
        sync();
    }
    function findLyrics() {
        const token = ++lyricRequest;
        lyricText = current?.lyrics || "";
        lyricStatus = current ? "Finding lyrics…" : "Choose a song to see lyrics.";
        if (!current || lyricText) { if (lyricText) lyricStatus = ""; return; }
        request("lyrics", {track: current}, data => {
            if (token !== lyricRequest) return;
            lyricText = data.text;
            lyricStatus = data.status;
            sync();
        });
    }
    function next(automatic) {
        if (spotifyPreview) { if (spotifyPlayer?.canGoNext) spotifyPlayer.next(); return; }
        if (!queue.length) return;
        if (automatic && repeatMode === "Track") { player.position = 0; player.play(); return; }
        if (shuffle && queue.length > 1) { select((currentIndex + 1 + Math.floor(Math.random()*(queue.length-1)))%queue.length); return; }
        if (currentIndex+1 < queue.length) select(currentIndex+1);
        else if (repeatMode === "Playlist") select(0);
    }
    function previous() { if (spotifyPreview) { if (spotifyPlayer?.canGoPrevious) spotifyPlayer.previous(); return; } if (player.position > 3000) player.position = 0; else select(Math.max(0,currentIndex-1)); }
    function toggle() { if (spotifyPreview) { if (spotifyPlayer?.canTogglePlaying) spotifyPlayer.togglePlaying(); return; } if (playing) player.pause(); else if (current) player.play(); else play(shownTracks); }
    function seek(value) { if (spotifyPreview) { if (spotifyPlayer?.canSeek) spotifyPlayer.position = value/1000; return; } player.position = Math.max(0, Math.min(player.duration, value)); sync(true); }
    function sync(seeked) {
        if (!backend.running) return;
        request("mpris", { track: localCurrent ? Object.assign({}, localCurrent, {lyrics: spotifyPreview ? "" : lyricText}) : null, status: !localCurrent || player.playbackState === MediaPlayer.StoppedState ? "Stopped" : player.playbackState === MediaPlayer.PlayingState ? "Playing" : "Paused",
            position: Math.round(player.position*1000), length: Math.round(player.duration*1000),
            volume: volume, shuffle: shuffle, loop: repeatMode, canNext: queue.length > 1,
            canPrevious: currentIndex > 0, seeked: !!seeked });
    }
    function control(message) {
        switch(message.action) {
        case "Raise": GlobalStates.musicWindowVisible = true; root.requestActivate(); break;
        case "PlayPause": toggle(); break;
        case "Play": if (current) player.play(); break;
        case "Pause": player.pause(); break;
        case "Stop": player.stop(); break;
        case "Next": next(false); break;
        case "Previous": previous(); break;
        case "Volume": volume = Math.max(0,Math.min(1,message.value)); break;
        case "Shuffle": shuffle = message.value; break;
        case "LoopStatus": repeatMode = message.value; break;
        case "Seek": seek(player.position+message.offset/1000); break;
        case "SetPosition": seek(message.position/1000); break;
        }
    }
    onVolumeChanged: sync()
    onShuffleChanged: sync()
    onRepeatModeChanged: sync()
    onPlayingChanged: sync()

    Process {
        id: backend
        command: ["python3", "-u", Qt.resolvedUrl("../../../scripts/music_library.py").toString().replace("file://", "")]
        stdinEnabled: true
        onStarted: root.scan()
        stdout: SplitParser { onRead: data => root.receive(data) }
        stderr: SplitParser { onRead: data => console.warn("Music: " + data) }
        onExited: { root.busy = false; root.notice = "Music service stopped. Reopen Music to retry."; root.started = false; }
    }
    // Follow output changes made while this window is open. An implicit
    // AudioOutput device otherwise retains the device selected at creation.
    MediaDevices { id: mediaDevices }
    MediaPlayer {
        id: player
        audioOutput: AudioOutput {
            volume: root.volume
            device: mediaDevices.defaultAudioOutput
        }
        onMediaStatusChanged: if (mediaStatus === MediaPlayer.EndOfMedia) root.next(true)
        onErrorOccurred: (error, errorString) => { root.notice = errorString; }
    }
    Timer { interval: 500; running: root.playing; repeat: true; onTriggered: root.sync() }
    Shortcut { sequence: "Space"; enabled: root.immersive || (root.page !== "Downloads" && root.page !== "Spotify playlists" && !search.inputActiveFocus && !playlistName.inputActiveFocus); onActivated: root.toggle() }
    Shortcut { sequence: "Ctrl+F"; enabled: root.page !== "Downloads" && root.page !== "Spotify playlists"; onActivated: search.focusInput() }
    Shortcut { sequence: "F11"; onActivated: root.toggleFullscreen() }
    Shortcut { sequence: "Escape"; onActivated: { if (root.immersive) root.toggleFullscreen(); else GlobalStates.musicWindowVisible = false; } }

    component Cover: ClippingRectangle {
        id: cover
        property string artwork: ""
        color: Colors.surfaceContainerHigh
        radius: Styling.radius(0)
        Image { id: image; anchors.fill: parent; source: cover.artwork; asynchronous: true; fillMode: Image.PreserveAspectCrop }
        StyledText { anchors.centerIn: parent; visible: image.status !== Image.Ready; text: "♫"; font.pixelSize: Math.min(cover.width*0.35,72); color: Colors.primary }
    }
    component TrackRow: StyledRect {
        id: row
        objectName: "music-track-row-" + number
        required property var track
        property int number: 0
        property bool selected: root.current?.path === track.path
        signal playRequested()
        signal enqueueRequested()
        width: ListView.view ? ListView.view.width : 0
        height: Styling.spacing(70)
        variant: selected || rowClick.containsMouse ? "focus" : "transparent"
        radius: Styling.radius(0)
        MouseArea {
            id: rowClick
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: row.playRequested()
        }
        RowLayout {
            anchors.fill: parent; anchors.margins: 8; spacing: 12
            ThemeButton { text: row.selected && root.playing ? "Ⅱ" : "▶"; Accessible.name: (row.selected && root.playing ? "Pause " : "Play ") + row.track.title; onClicked: row.playRequested() }
            Cover { artwork: row.track.art; Layout.preferredWidth: 48; Layout.preferredHeight: 48 }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                StyledText { Layout.fillWidth: true; text: row.track.title; elide: Text.ElideRight; color: row.selected ? Colors.primary : Colors.overSurface }
                StyledText { Layout.fillWidth: true; text: row.track.artist + " · " + row.track.album; color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-2); elide: Text.ElideRight }
            }
            StyledText { text: root.time(row.track.duration*1000); color: Colors.overSurfaceVariant }
            ThemeButton { text: root.favorites.includes(row.track.path) ? "♥" : "♡"; Accessible.name: "Favorite " + row.track.title; onClicked: root.favorite(row.track) }
            ThemeButton { objectName: "music-track-queue-" + row.number; text: "+"; Accessible.name: "Queue " + row.track.title; onClicked: row.enqueueRequested() }
        }
    }

    StyledRect {
        visible: !root.immersive
        objectName: "music-background"
        anchors.fill: parent; variant: "bg"; radius: 0
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 16; spacing: 12
            StyledRect {
                objectName: "music-top-navigation"
                Layout.fillWidth: true
                implicitHeight: topNavigation.implicitHeight + Styling.spacing(24)
                variant: "pane"
                ColumnLayout {
                    id: topNavigation
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.margins: Styling.spacing(12)
                    spacing: Styling.spacing(8)
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: "Enclosure Music"; font.bold: true; font.pixelSize: Styling.fontSize(2) }
                        StyledText { Layout.fillWidth: true; text: root.tracks.length + " songs"; color: Colors.overSurfaceVariant; elide: Text.ElideRight }
                        ThemeButton { objectName: "music-fullscreen-enter"; text: "Fullscreen"; Accessible.name: "Enter fullscreen listening view (F11)"; onClicked: root.toggleFullscreen() }
                        ThemeButton { text: "Add folder"; enabled: !root.busy; onClicked: { root.busy = true; root.request("folder", {}, root.load); } }
                        ThemeButton { text: root.busy ? "Scanning…" : "Refresh library"; enabled: !root.busy; onClicked: root.scan() }
                    }
                    Flow {
                        id: navigationTabs
                        objectName: "music-navigation-tabs"
                        readonly property int tabCount: navigationModel.length
                        readonly property var navigationModel: ["Songs", "Albums", "Artists", "Favorites", "Playlists", "Spotify playlists", "Downloads", "Now playing"]
                        readonly property int rowCount: Math.max(1, Math.ceil(tabCount * (Styling.spacing(112) + spacing) / Math.max(1, width + spacing)))
                        readonly property int columns: Math.ceil(tabCount / rowCount)
                        readonly property int lastRowCount: tabCount % columns || columns
                        Layout.fillWidth: true
                        spacing: Styling.spacing(6)
                        Repeater {
                            model: navigationTabs.navigationModel
                            ThemeButton {
                                required property string modelData
                                required property int index
                                readonly property int rowColumns: index >= navigationTabs.tabCount - navigationTabs.lastRowCount ? navigationTabs.lastRowCount : navigationTabs.columns
                                width: Math.max(1, (navigationTabs.width - navigationTabs.spacing * (rowColumns - 1)) / rowColumns)
                                objectName: "music-navigation-" + modelData
                                text: modelData
                                highlighted: root.page === modelData
                                onClicked: root.navigate(modelData)
                            }
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: Styling.spacing(16)
                ColumnLayout {
                    visible: root.page !== "Downloads" && root.page !== "Spotify playlists" && (root.width >= 1120 || root.page !== "Now playing")
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 14
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: root.pageTitle; font.pixelSize: Styling.fontSize(14); font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                        SearchInput { id: search; Layout.preferredWidth: Math.min(300, root.width*0.25); placeholderText: "Search music"; text: root.query; onSearchTextChanged: text => root.query = text }
                    }
                    StyledText { Layout.fillWidth: true; visible: root.notice !== ""; text: root.notice; wrapMode: Text.WordWrap; color: Colors.error }
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: root.shownTracks.length + " songs · Your library"; color: Colors.overSurfaceVariant; Layout.fillWidth: true }
                        ThemeButton { text: "Play all"; highlighted: true; enabled: root.shownTracks.length > 0; onClicked: root.play(root.shownTracks) }
                        ThemeButton { text: "Shuffle"; enabled: root.shownTracks.length > 0; onClicked: { root.shuffle = true; root.play(root.shownTracks,Math.floor(Math.random()*root.shownTracks.length)); } }
                    }
                    // Album shelves and artist cards follow the downloaded reference's library layout.
                    GridView {
                        id: cards
                        visible: ["Albums","Artists","Playlists"].includes(root.page)
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        cellWidth: Math.max(160, Math.floor(width/Math.max(1,Math.floor(width/190))))
                        cellHeight: cellWidth + 62
                        model: root.page === "Artists" ? root.artists : (root.page === "Playlists") ? root.playlists.map(p => ({key:p.id,title:p.name,subtitle:(p.mix ? p.sourceName + " · " : "") + p.paths.length + " songs",art:root.tracks.find(t=>t.path === p.paths[0])?.art || ""})) : root.albums
                        delegate: Item {
                            id: card
                            required property var modelData
                            readonly property var playableTracks: root.cardTracks(root.page, modelData.key)
                            width: cards.cellWidth; height: cards.cellHeight
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 8; spacing: 6
                                Cover {
                                    Layout.fillWidth: true; Layout.preferredHeight: card.width-16; artwork: card.modelData.art
                                    ThemeButton {
                                        objectName: "music-card-play"
                                        anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 10
                                        text: "▶"; highlighted: true
                                        Accessible.name: "Play " + card.modelData.title
                                        enabled: card.playableTracks.length > 0
                                        onClicked: root.play(card.playableTracks)
                                    }
                                }
                                ThemeButton {
                                    Layout.fillWidth: true; text: card.modelData.title
                                    onClicked: root.navigate(root.page === "Artists" ? "Artist" : (root.page === "Playlists") ? "Playlist" : "Album",card.modelData.key)
                                }
                                StyledText { Layout.fillWidth: true; text: card.modelData.subtitle; elide: Text.ElideRight; color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-2) }
                            }
                        }
                        ScrollBar.vertical: ScrollBar {}
                        StyledText { anchors.centerIn: parent; width: parent.width-48; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; visible: cards.count === 0; text: root.busy ? "Scanning music…" : root.page === "Playlists" ? "Create a playlist from the queue below or download a mix from Spotify playlists." : "No music found.\nAdd a folder or change the search."; color: Colors.overSurfaceVariant }
                    }
                    ListView {
                        id: songs
                        visible: !cards.visible
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 4
                        model: root.shownTracks
                        delegate: TrackRow {
                            required property var modelData
                            required property int index
                            track: modelData; number: index
                            onPlayRequested: { if (selected) root.toggle(); else root.play(root.shownTracks,index); }
                            onEnqueueRequested: root.enqueue(track)
                        }
                        ScrollBar.vertical: ScrollBar {}
                        StyledText { anchors.centerIn: parent; visible: songs.count === 0; text: root.query ? "No matching songs" : "No songs"; color: Colors.overSurfaceVariant }
                    }
                    ColumnLayout {
                        visible: root.page === "Playlist"
                        Layout.fillWidth: true
                        RowLayout {
                            Layout.fillWidth: true
                            StyledText { text: "Suggested tracks · Spotify"; font.bold: true; Layout.fillWidth: true }
                            ThemeButton { text: root.spotifySuggestions.pending ? "Loading…" : "Refresh"; enabled: !root.spotifySuggestions.pending; onClicked: root.refreshSuggestions() }
                        }
                        StyledText {
                            visible: root.suggestedTracks.length === 0
                            Layout.fillWidth: true; wrapMode: Text.WordWrap
                            text: root.spotifySuggestions.status || "Open Spotify, then refresh suggestions for this playlist."
                            color: Colors.overSurfaceVariant
                        }
                        ListView {
                            objectName: "music-playlist-suggestions"
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.min(count, 3) * Styling.spacing(52)
                            clip: true; model: root.suggestedTracks
                            delegate: RowLayout {
                                id: suggestion
                                required property var modelData
                                width: ListView.view.width; height: Styling.spacing(52)
                                StyledText { Layout.fillWidth: true; text: suggestion.modelData.title + " · " + suggestion.modelData.artist; elide: Text.ElideRight }
                                ThemeButton { text: "Play"; Accessible.name: "Play suggested track " + suggestion.modelData.title; onClicked: root.previewTrack(suggestion.modelData.uri) }
                                ThemeButton {
                                    text: "Add"; Accessible.name: "Add " + suggestion.modelData.title + " to playlist"
                                    enabled: !root.busy && !downloads.busy && !root.pendingSuggestionDownload
                                    onClicked: {
                                        const local = root.tracks.find(t => t.spotifyUri === suggestion.modelData.uri);
                                        if (local) root.request("playlist_add", {playlist:root.detail, path:local.path}, root.load);
                                        else root.request("suggestion_download", {playlist:root.detail, uri:suggestion.modelData.uri}, data => {
                                            if (downloads.prepareSuggestion(data)) {
                                                root.pendingSuggestionDownload = data;
                                                downloads.start();
                                            }
                                        });
                                    }
                                }
                            }
                            ScrollBar.vertical: ScrollBar {}
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        SearchInput { id: playlistName; Layout.fillWidth: true; placeholderText: "Name a playlist from the queue" }
                        ThemeButton {
                            text: "Save queue"; enabled: playlistName.text.trim() !== "" && root.queue.length > 0
                            onClicked: {
                                root.playlists = root.playlists.concat([{id: Date.now().toString(),name: playlistName.text.trim(),paths: root.queue.map(t=>t.path)}]);
                                root.save(); playlistName.clear(); root.navigate("Playlists");
                            }
                        }
                    }
                }
                DailyMixesPane {
                    id: dailyMixes
                    importedPlaylists: root.playlists
                    localTracks: root.tracks
                    currentPath: root.current?.path || ""
                    notice: root.notice
                    downloadBusy: downloads.busy
                    onPlayRequested: (list, index) => root.play(list, index)
                    onPreviewRequested: uri => root.request("mixes_preview", {uri: uri}, data => {
                        player.pause();
                        dailyMixes.previewStatus = data.status;
                    })
                    onDownloadRequested: mix => root.request("mixes_download", {uri: mix.uri, version: mix.version}, data => {
                        if (downloads.prepareMix(data)) root.navigate("Downloads");
                    })
                    visible: root.page === "Spotify playlists"
                    Layout.fillWidth: true; Layout.fillHeight: true
                    onRequested: (cmd, args, callback) => root.request(cmd, args, callback)
                }
                DownloadsPane {
                    id: downloads
                    visible: root.page === "Downloads"
                    Layout.fillWidth: true; Layout.fillHeight: true
                    onRejected: { root.pendingSuggestionDownload = null; root.notice = "Download could not start. Check Downloads for details."; }
                    onCompleted: {
                        const pending = root.pendingSuggestionDownload;
                        root.pendingSuggestionDownload = null;
                        if (!pending) { root.scan(); return; }
                        root.request("scan", {}, data => {
                            root.load(data);
                            const track = data.tracks.find(t => t.spotifyUri === pending.uri);
                            if (track) root.request("playlist_add", {playlist:pending.playlist, path:track.path}, root.load);
                            else root.notice = "Track was not downloaded. Check the Downloads activity log and try again.";
                        });
                    }
                }
                StyledRect {
                    visible: root.page !== "Downloads" && root.page !== "Spotify playlists" && (root.width >= 1120 || root.page === "Now playing")
                    Layout.fillWidth: root.width < 1120
                    Layout.preferredWidth: 280; Layout.fillHeight: true; variant: "pane"
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 14; spacing: 12
                        Cover { Layout.fillWidth: true; Layout.preferredHeight: 230; artwork: root.current?.art || "" }
                        StyledText { Layout.fillWidth: true; text: root.current?.title || "Nothing playing"; wrapMode: Text.WordWrap; font.bold: true; font.pixelSize: Styling.fontSize(4) }
                        StyledText { Layout.fillWidth: true; text: root.current?.artist || "Select a song to play"; elide: Text.ElideRight; color: Colors.overSurfaceVariant }
                        RowLayout {
                            ThemeButton { text: "Queue"; highlighted: root.side === "Queue"; onClicked: root.side = "Queue" }
                            ThemeButton { text: "Lyrics"; highlighted: root.side === "Lyrics"; onClicked: root.side = "Lyrics" }
                            Item { Layout.fillWidth: true }
                        }
                        ListView {
                            id: queueList
                            visible: root.side === "Queue"; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 5
                            model: root.queue
                            delegate: ThemeButton {
                                required property var modelData
                                required property int index
                                width: queueList.width; text: (index+1) + "  " + modelData.title; highlighted: index === root.currentIndex
                                onClicked: root.select(index)
                            }
                            ScrollBar.vertical: ScrollBar {}
                        }
                        StyledText {
                            visible: root.side === "Lyrics" && root.estimatedTiming
                            text: "Estimated timing · line positions may differ from the vocals"
                            Layout.fillWidth: true; wrapMode: Text.WordWrap
                            color: Colors.overSurfaceVariant
                            font.pixelSize: Styling.fontSize(-2)
                        }
                        ListView {
                            id: lyricsList
                            visible: root.side === "Lyrics"; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 14
                            model: root.lyricLines
                            delegate: StyledText {
                                required property var modelData
                                required property int index
                                width: lyricsList.width; text: modelData.text; wrapMode: Text.WordWrap
                                color: index === root.lyricIndex ? Colors.primary : Colors.overSurfaceVariant
                                font.bold: index === root.lyricIndex
                            }
                            ScrollBar.vertical: ScrollBar {}
                            StyledText { anchors.fill: parent; visible: root.lyricLines.length === 0; text: root.lyricStatus; wrapMode: Text.WordWrap; color: Colors.overSurfaceVariant }
                        }
                    }
                }
            }
            StyledRect {
                Layout.fillWidth: true; implicitHeight: 112; variant: "pane"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 2
                    RowLayout {
                        Layout.fillWidth: true
                        Cover { artwork: root.current?.art || ""; Layout.preferredWidth: 46; Layout.preferredHeight: 46 }
                        ColumnLayout {
                            Layout.fillWidth: true
                            RowLayout {
                                Layout.fillWidth: true
                                StyledText {
                                    Layout.minimumWidth: 0
                                    Layout.preferredWidth: implicitWidth
                                    Layout.maximumWidth: Math.max(0, parent.width - currentFavorite.width - parent.spacing)
                                    text: root.current?.title || "Enclosure Music"; elide: Text.ElideRight
                                }
                                ThemeButton {
                                    id: currentFavorite
                                    objectName: "music-favorite-current"
                                    enabled: !!root.current
                                    checked: !!root.current && root.favorites.includes(root.current.path)
                                    text: checked ? "♥" : "♡"
                                    Accessible.name: checked ? "Remove current song from favorites" : "Add current song to favorites"
                                    ToolTip.visible: hovered
                                    ToolTip.text: Accessible.name
                                    onClicked: if (root.current) root.favorite(root.current)
                                }
                                Item { Layout.fillWidth: true }
                            }
                            StyledText { Layout.fillWidth: true; text: root.current?.artist || "Local music library"; elide: Text.ElideRight; color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-2) }
                        }
                        ThemeButton { text: "Shuffle"; checked: root.shuffle; onClicked: root.shuffle = !root.shuffle }
                        ThemeButton { text: "⏮"; Accessible.name: "Previous track"; enabled: !!root.current; onClicked: root.previous() }
                        ThemeButton { text: root.playing ? "Pause" : "Play"; highlighted: true; enabled: root.queue.length > 0 || root.shownTracks.length > 0; onClicked: root.toggle() }
                        ThemeButton { text: "⏭"; Accessible.name: "Next track"; enabled: root.queue.length > 1; onClicked: root.next(false) }
                        ThemeButton {
                            objectName: "music-repeat"
                            text: root.repeatMode === "Track" ? "Repeat song" : root.repeatMode === "Playlist" ? "Repeat all" : "Repeat off"
                            checked: root.repeatMode !== "None"
                            Accessible.name: text + ". Click to change repeat mode"
                            ToolTip.visible: hovered
                            ToolTip.text: "Cycle repeat: off → all → song"
                            onClicked: root.repeatMode = root.repeatMode === "None" ? "Playlist" : root.repeatMode === "Playlist" ? "Track" : "None"
                        }
                        ThemeSlider { Layout.preferredWidth: 90; from: 0; to: 1; value: root.volume; Accessible.name: "Volume"; onMoved: root.volume = value }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: root.time(player.position); font.pixelSize: Styling.fontSize(-2) }
                        ThemeSlider { id: seekSlider; Layout.fillWidth: true; from: 0; to: Math.max(1,player.duration); value: player.position; enabled: !!root.current; Accessible.name: "Seek"; onMoved: root.seek(value) }
                        StyledText { text: root.time(player.duration); font.pixelSize: Styling.fontSize(-2) }
                    }
                }
            }
        }
    }

    // A listening stage: artwork, lyrics and transport share the existing player.
    Rectangle {
        id: stage
        objectName: "music-fullscreen-stage"
        anchors.fill: parent
        visible: root.immersive
        color: Colors.surface
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.tint(Colors.surface, Qt.alpha(Colors.primary, 0.18)) }
            GradientStop { position: 0.65; color: Colors.surface }
            GradientStop { position: 1; color: Qt.tint(Colors.surface, Qt.alpha(Colors.primary, 0.06)) }
        }
        readonly property real inset: Math.max(24, Math.min(width * 0.045, 80))
        readonly property bool wide: width >= 1100
        ColumnLayout {
            anchors.fill: parent; anchors.margins: stage.inset
            spacing: Math.max(18, stage.height * 0.025)
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    spacing: 4
                    StyledText { text: root.spotifyPreview ? "NOW PLAYING · SPOTIFY" : "NOW PLAYING"; font.pixelSize: Styling.fontSize(-2); font.letterSpacing: 3; color: Colors.primary }
                    StyledText { text: root.current?.album || "Your listening room"; elide: Text.ElideRight; Layout.maximumWidth: stage.width * 0.6; color: Colors.overSurfaceVariant }
                }
                Item { Layout.fillWidth: true }
                ThemeButton { objectName: "music-fullscreen-exit"; text: "Exit fullscreen · Esc"; onClicked: root.toggleFullscreen() }
            }
            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                spacing: stage.inset
                ColumnLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    Layout.preferredWidth: stage.wide ? stage.width * 0.42 : stage.width
                    spacing: 18
                    Item { Layout.fillHeight: true }
                    Cover {
                        objectName: "music-fullscreen-art"
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: Math.max(100, Math.min(stage.wide ? stage.width * 0.36 : stage.width * 0.5, stage.height * 0.46))
                        Layout.preferredHeight: width
                        artwork: root.current?.art || ""
                        radius: Styling.radius(8)
                        border.width: 1; border.color: Qt.alpha(Colors.outline, 0.25)
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 8
                        StyledText { Layout.fillWidth: true; text: root.current?.title || "Find your next favorite"; font.pixelSize: Math.min(40, stage.height * 0.044); font.bold: true; maximumLineCount: 2; wrapMode: Text.Wrap; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter }
                        StyledText { Layout.fillWidth: true; text: root.current?.artist || "Choose a song from your library"; font.pixelSize: Styling.fontSize(4); color: Colors.overSurfaceVariant; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter }
                    }
                    Item { Layout.fillHeight: true }
                }
                ColumnLayout {
                    visible: stage.wide
                    Layout.fillWidth: true; Layout.fillHeight: true
                    Layout.preferredWidth: stage.width * 0.45
                    spacing: 16
                    StyledText { text: "LYRICS"; font.pixelSize: Styling.fontSize(-2); font.letterSpacing: 3; color: Colors.primary }
                    ListView {
                        id: fullscreenLyrics
                        objectName: "music-fullscreen-lyrics"
                        Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true; spacing: 26
                        model: root.lyricLines
                        topMargin: height * 0.28; bottomMargin: height * 0.28
                        onVisibleChanged: if (visible && root.lyricIndex >= 0) positionViewAtIndex(root.lyricIndex, ListView.Center)
                        delegate: ContentText {
                            required property var modelData
                            required property int index
                            width: fullscreenLyrics.width
                            text: modelData.text; wrapMode: Text.WordWrap
                            font.pixelSize: Math.min(36, stage.height * 0.04); font.bold: true
                            color: index === root.lyricIndex ? Colors.primary : Colors.overSurfaceVariant
                            opacity: index === root.lyricIndex ? 1 : 0.55
                        }
                        StyledText { anchors.centerIn: parent; width: parent.width; text: root.lyricStatus || "Let the music speak."; visible: root.lyricLines.length === 0; wrapMode: Text.WordWrap; font.pixelSize: Styling.fontSize(8); color: Colors.overSurfaceVariant }
                    }
                    StyledText { visible: root.estimatedTiming; text: "Estimated lyric timing"; color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-2) }
                }
            }
            StyledText { visible: root.notice !== ""; Layout.fillWidth: true; text: root.notice; elide: Text.ElideRight; color: Colors.error }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 14
                RowLayout {
                    Layout.fillWidth: true; spacing: 14
                    StyledText { text: root.time(root.playbackPosition); color: Colors.overSurfaceVariant }
                    ThemeSlider { objectName: "music-fullscreen-seek"; Layout.fillWidth: true; from: 0; to: Math.max(1, root.playbackDuration); value: root.playbackPosition; enabled: root.spotifyPreview ? !!root.spotifyPlayer?.canSeek : !!root.current; Accessible.name: "Seek"; onMoved: root.seek(value) }
                    StyledText { text: root.time(root.playbackDuration); color: Colors.overSurfaceVariant }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 12
                    ThemeButton { text: root.favorites.includes(root.current?.path) ? "♥" : "♡"; enabled: !!root.current && !root.spotifyPreview; Accessible.name: "Favorite current song"; onClicked: root.favorite(root.current) }
                    Item { Layout.fillWidth: true }
                    ThemeButton { objectName: "music-fullscreen-shuffle"; text: "Shuffle"; checked: root.spotifyPreview ? !!root.spotifyPlayer?.shuffle : root.shuffle; enabled: !root.spotifyPreview || !!root.spotifyPlayer?.shuffleSupported; onClicked: { if (root.spotifyPreview) root.spotifyPlayer.shuffle = !root.spotifyPlayer.shuffle; else root.shuffle = !root.shuffle; } }
                    ThemeButton { objectName: "music-fullscreen-previous"; text: "⏮"; Accessible.name: "Previous track"; enabled: root.spotifyPreview ? !!root.spotifyPlayer?.canGoPrevious : !!root.current; onClicked: root.previous() }
                    ThemeButton { objectName: "music-fullscreen-play"; text: root.playing ? "Pause" : "Play"; highlighted: true; Layout.preferredWidth: 120; implicitHeight: 52; enabled: root.spotifyPreview ? !!root.spotifyPlayer?.canTogglePlaying : root.queue.length > 0 || root.shownTracks.length > 0; onClicked: root.toggle() }
                    ThemeButton { objectName: "music-fullscreen-next"; text: "⏭"; Accessible.name: "Next track"; enabled: root.spotifyPreview ? !!root.spotifyPlayer?.canGoNext : root.queue.length > 1; onClicked: root.next(false) }
                    ThemeButton { objectName: "music-fullscreen-repeat"; text: root.spotifyPreview ? (root.spotifyPlayer?.loopState === MprisLoopState.Track ? "Repeat song" : "Repeat all") : root.repeatMode === "Track" ? "Repeat song" : "Repeat all"; checked: root.spotifyPreview ? root.spotifyPlayer?.loopState !== MprisLoopState.None : root.repeatMode !== "None"; enabled: !root.spotifyPreview || !!root.spotifyPlayer?.loopSupported; onClicked: {
                        if (root.spotifyPreview) root.spotifyPlayer.loopState = root.spotifyPlayer.loopState === MprisLoopState.None ? MprisLoopState.Playlist : root.spotifyPlayer.loopState === MprisLoopState.Playlist ? MprisLoopState.Track : MprisLoopState.None;
                        else root.repeatMode = root.repeatMode === "None" ? "Playlist" : root.repeatMode === "Playlist" ? "Track" : "None";
                    } }
                    Item { Layout.fillWidth: true }
                    ThemeSlider { objectName: "music-fullscreen-volume"; Layout.preferredWidth: 100; from: 0; to: 1; value: root.spotifyPreview ? (root.spotifyPlayer?.volume || 0) : root.volume; enabled: !root.spotifyPreview || !!root.spotifyPlayer?.volumeSupported; Accessible.name: "Volume"; onMoved: { if (root.spotifyPreview) root.spotifyPlayer.volume = value; else root.volume = value; } }
                }
            }
        }
    }
}
