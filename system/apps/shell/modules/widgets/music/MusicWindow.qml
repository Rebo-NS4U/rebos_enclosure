pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import Quickshell
import Quickshell.Io
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
    color: Colors.background
    visible: GlobalStates.musicWindowVisible
    onClosing: event => { event.accepted = false; GlobalStates.musicWindowVisible = false; }
    onVisibleChanged: if (visible && !started) { started = true; backend.running = true; }

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
    property string page: "Home"
    property string query: ""
    property string detail: ""
    property string side: "Queue"
    property var queue: []
    property int currentIndex: -1
    property bool shuffle: false
    property string repeatMode: "None"
    property real volume: 0.8
    property int requestId: 0
    property var callbacks: ({})
    readonly property var current: currentIndex >= 0 && currentIndex < queue.length ? queue[currentIndex] : null
    readonly property bool playing: player.playbackState === MediaPlayer.PlayingState
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
        if (estimatedTiming) return Lyrics.estimatedLines(raw, player.duration > 0 ? player.duration/1000 : (current?.duration || 0));
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
        for (let i = 0; i < lyricLines.length; i++) if (lyricLines[i].time >= 0 && lyricLines[i].time <= player.position/1000) found = i;
        return found;
    }
    onLyricIndexChanged: if (lyricIndex >= 0) lyricsList.positionViewAtIndex(lyricIndex, ListView.Center)

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
        if (!message.ok) { busy = false; notice = message.error; return; }
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
        favorites = favorites.includes(track.path) ? favorites.filter(p => p !== track.path) : favorites.concat([track.path]); save();
    }
    function navigate(value, arg) { page = value; detail = arg || ""; query = ""; }
    function play(list, index) { if (!list.length) return; queue = list.slice(); select(index || 0); }
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
        if (!queue.length) return;
        if (automatic && repeatMode === "Track") { player.position = 0; player.play(); return; }
        if (shuffle && queue.length > 1) { select((currentIndex + 1 + Math.floor(Math.random()*(queue.length-1)))%queue.length); return; }
        if (currentIndex+1 < queue.length) select(currentIndex+1);
        else if (repeatMode === "Playlist") select(0);
    }
    function previous() { if (player.position > 3000) player.position = 0; else select(Math.max(0,currentIndex-1)); }
    function toggle() { if (playing) player.pause(); else if (current) player.play(); else play(shownTracks,0); }
    function seek(value) { player.position = Math.max(0, Math.min(player.duration, value)); sync(true); }
    function sync(seeked) {
        if (!backend.running) return;
        request("mpris", { track: current ? Object.assign({}, current, {lyrics: lyricText}) : null, status: !current || player.playbackState === MediaPlayer.StoppedState ? "Stopped" : playing ? "Playing" : "Paused",
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
    MediaPlayer {
        id: player
        audioOutput: AudioOutput { volume: root.volume }
        onMediaStatusChanged: if (mediaStatus === MediaPlayer.EndOfMedia) root.next(true)
        onErrorOccurred: (error, errorString) => { root.notice = errorString; }
    }
    Timer { interval: 500; running: root.playing; repeat: true; onTriggered: root.sync() }
    Shortcut { sequence: "Space"; enabled: !search.inputActiveFocus && !playlistName.inputActiveFocus; onActivated: root.toggle() }
    Shortcut { sequence: "Ctrl+F"; onActivated: search.focusInput() }
    Shortcut { sequence: "Escape"; onActivated: GlobalStates.musicWindowVisible = false }

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
        required property var track
        property int number: 0
        property bool selected: root.current?.path === track.path
        signal playRequested()
        signal enqueueRequested()
        width: ListView.view ? ListView.view.width : 0
        height: Styling.spacing(70)
        variant: selected ? "focus" : "transparent"
        radius: Styling.radius(0)
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
            ThemeButton { text: "+"; Accessible.name: "Queue " + row.track.title; onClicked: row.enqueueRequested() }
        }
    }

    StyledRect {
        anchors.fill: parent; variant: "bg"; radius: 0
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 16; spacing: 12
            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 16
                StyledRect {
                    Layout.preferredWidth: 180; Layout.fillHeight: true; variant: "pane"
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 16; spacing: 10
                        StyledText { text: "MUSIC"; color: Colors.primary; font.bold: true; font.letterSpacing: 3; font.pixelSize: Styling.fontSize(5); Layout.topMargin: 12; Layout.bottomMargin: 18 }
                        Repeater {
                            model: ["Home", "Songs", "Albums", "Artists", "Favorites", "Playlists", "Now playing"]
                            delegate: ThemeButton {
                                required property string modelData
                                Layout.fillWidth: true; text: modelData; highlighted: root.page === modelData
                                onClicked: root.navigate(modelData)
                            }
                        }
                        Item { Layout.fillHeight: true }
                        StyledText { Layout.fillWidth: true; text: root.tracks.length + " songs in library"; wrapMode: Text.WordWrap; color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-2) }
                        ThemeButton { Layout.fillWidth: true; text: "Add folder"; enabled: !root.busy; onClicked: { root.busy = true; root.request("folder", {}, root.load); } }
                        ThemeButton { Layout.fillWidth: true; text: root.busy ? "Scanning…" : "Refresh library"; enabled: !root.busy; onClicked: root.scan() }
                    }
                }
                ColumnLayout {
                    visible: root.width >= 1120 || root.page !== "Now playing"
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 14
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: root.pageTitle; font.pixelSize: Styling.fontSize(14); font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                        SearchInput { id: search; Layout.preferredWidth: Math.min(300, root.width*0.25); placeholderText: "Search your music"; text: root.query; onSearchTextChanged: text => root.query = text }
                    }
                    StyledText { Layout.fillWidth: true; visible: root.notice !== ""; text: root.notice; wrapMode: Text.WordWrap; color: Colors.error }
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: root.page === "Home" ? "Your music, close at hand" : root.shownTracks.length + " songs"; color: Colors.overSurfaceVariant; Layout.fillWidth: true }
                        ThemeButton { text: "Play all"; highlighted: true; enabled: root.shownTracks.length > 0; onClicked: root.play(root.shownTracks,0) }
                        ThemeButton { text: "Shuffle"; enabled: root.shownTracks.length > 0; onClicked: { root.shuffle = true; root.play(root.shownTracks,Math.floor(Math.random()*root.shownTracks.length)); } }
                    }
                    // Album shelves and artist cards follow the downloaded reference's library layout.
                    GridView {
                        id: cards
                        visible: ["Home","Albums","Artists","Playlists"].includes(root.page)
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        cellWidth: Math.max(160, Math.floor(width/Math.max(1,Math.floor(width/190))))
                        cellHeight: cellWidth + 62
                        model: root.page === "Artists" ? root.artists : root.page === "Playlists" ? root.playlists.map(p => ({key:p.id,title:p.name,subtitle:p.paths.length + " songs",art:root.tracks.find(t=>t.path === p.paths[0])?.art || ""})) : root.albums
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
                                        onClicked: root.play(card.playableTracks, 0)
                                    }
                                }
                                ThemeButton {
                                    Layout.fillWidth: true; text: card.modelData.title
                                    onClicked: root.navigate(root.page === "Artists" ? "Artist" : root.page === "Playlists" ? "Playlist" : "Album",card.modelData.key)
                                }
                                StyledText { Layout.fillWidth: true; text: card.modelData.subtitle; elide: Text.ElideRight; color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-2) }
                            }
                        }
                        ScrollBar.vertical: ScrollBar {}
                        StyledText { anchors.centerIn: parent; width: parent.width-48; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; visible: cards.count === 0; text: root.busy ? "Reading your music…" : root.page === "Playlists" ? "Create a playlist from the queue below." : "Your library starts here.\nAdd a music folder to see albums and artists."; color: Colors.overSurfaceVariant }
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
                            onEnqueueRequested: root.queue = root.queue.concat([track])
                        }
                        ScrollBar.vertical: ScrollBar {}
                        StyledText { anchors.centerIn: parent; visible: songs.count === 0; text: root.query ? "No matching songs" : "No songs here yet"; color: Colors.overSurfaceVariant }
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
                StyledRect {
                    visible: root.width >= 1120 || root.page === "Now playing"
                    Layout.fillWidth: root.width < 1120
                    Layout.preferredWidth: 280; Layout.fillHeight: true; variant: "pane"
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 14; spacing: 12
                        Cover { Layout.fillWidth: true; Layout.preferredHeight: 230; artwork: root.current?.art || "" }
                        StyledText { Layout.fillWidth: true; text: root.current?.title || "Nothing playing yet"; wrapMode: Text.WordWrap; font.bold: true; font.pixelSize: Styling.fontSize(4) }
                        StyledText { Layout.fillWidth: true; text: root.current?.artist || "Choose a song to get started"; elide: Text.ElideRight; color: Colors.overSurfaceVariant }
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
                            StyledText { Layout.fillWidth: true; text: root.current?.title || "Enclosure Music"; elide: Text.ElideRight }
                            StyledText { Layout.fillWidth: true; text: root.current?.artist || "Your local music library"; elide: Text.ElideRight; color: Colors.overSurfaceVariant; font.pixelSize: Styling.fontSize(-2) }
                        }
                        ThemeButton { text: "Shuffle"; checked: root.shuffle; onClicked: root.shuffle = !root.shuffle }
                        ThemeButton { text: "⏮"; Accessible.name: "Previous track"; enabled: !!root.current; onClicked: root.previous() }
                        ThemeButton { text: root.playing ? "Pause" : "Play"; highlighted: true; enabled: root.queue.length > 0 || root.shownTracks.length > 0; onClicked: root.toggle() }
                        ThemeButton { text: "⏭"; Accessible.name: "Next track"; enabled: root.queue.length > 1; onClicked: root.next(false) }
                        ThemeButton {
                            objectName: "music-repeat-song"
                            text: "Repeat song"; checkable: true; checked: root.repeatMode === "Track"
                            highlighted: checked
                            Accessible.name: "Repeat current song"
                            onClicked: root.repeatMode = root.repeatMode === "Track" ? "None" : "Track"
                        }
                        ThemeButton {
                            text: "Repeat all"; checkable: true; checked: root.repeatMode === "Playlist"
                            onClicked: root.repeatMode = root.repeatMode === "Playlist" ? "None" : "Playlist"
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
}
