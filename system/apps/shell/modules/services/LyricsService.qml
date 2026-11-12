pragma Singleton
import QtQuick
import Quickshell
import "Lyrics.js" as Lyrics

Singleton {
    id: root
    property string pinEdge: ""
    property string lastPinEdge: "bottom"
    property string pinScreen: ""
    property int viewers: 0
    readonly property bool wanted: viewers > 0 || pinEdge !== ""
    readonly property var player: MprisController.activePlayer
    readonly property string supplied: Lyrics.playerLyrics(player?.metadata)
    readonly property string trackKey: JSON.stringify([player?.dbusName, MprisController.trackTitle,
        MprisController.trackArtists, player?.trackAlbum, Math.round(MprisController.length)])
    property string lyricsKey: ""
    readonly property bool hasLyrics: player !== null && lyricsKey === trackKey && plain.trim().length > 0
    property string plain: ""
    property var lines: []
    property string status: "Play a song to see lyrics."
    property string provider: ""
    property var createRequest: () => new XMLHttpRequest()
    property var request: null
    property var cache: ({})
    readonly property int currentLine: playbackClock.activeIndex
    readonly property int followLine: playbackClock.followIndex
    property LyricsClock playbackClock: LyricsClock {
        lines: root.lines
        position: MprisController.position
        playing: MprisController.isPlaying
        rate: root.player?.rate ?? 1
        enabled: root.wanted && root.hasLyrics
        trackKey: root.trackKey
    }

    function toggle(screenName) {
        if (pinEdge !== "") pinEdge = "";
        else pin(lastPinEdge, screenName);
    }
    function pin(edge, screenName) {
        lastPinEdge = edge;
        pinScreen = screenName || Quickshell.screens[0]?.name || "";
        pinEdge = edge;
    }
    function cancel() {
        const pending = request;
        request = null;
        timeout.stop();
        if (pending) pending.abort();
    }
    function apply(text, source, instrumental) {
        lyricsKey = trackKey;
        lines = instrumental ? [] : Lyrics.parseLrc(text);
        plain = instrumental ? "" : (lines.length ? lines.map(line => line.text).join("\n") : text);
        provider = source;
        status = instrumental ? "Instrumental — no lyrics." : (plain ? "" : "No lyrics found for this song.");
    }
    function refresh() {
        cancel();
        plain = ""; lines = []; provider = "";
        if (!player || !MprisController.trackTitle) {
            status = "Play a song to see lyrics."; return;
        }
        if (supplied) {
            apply(supplied, player.identity || "Player", false); return;
        }
        if (!wanted) { status = ""; return; }
        const key = trackKey;
        if (cache[key]) {
            const hit = cache[key]; apply(hit.text, "LRCLIB", hit.instrumental); return;
        }
        if (!MprisController.trackArtists) {
            status = "Artist information is needed to find lyrics."; return;
        }
        status = "Finding lyrics on LRCLIB…";
        lookup(key, false);
    }
    function lookup(key, searching) {
        const title = MprisController.trackTitle;
        const artists = MprisController.trackArtists;
        const album = player?.trackAlbum || "";
        const duration = MprisController.length;
        const xhr = createRequest();
        request = xhr;
        let url = "https://lrclib.net/api/" + (searching ? "search" : "get")
            + "?track_name=" + encodeURIComponent(title)
            + "&artist_name=" + encodeURIComponent(searching ? Lyrics.primaryArtist(artists) : artists);
        if (!searching) {
            if (album) url += "&album_name=" + encodeURIComponent(album);
            // LRCLIB rejects durations outside this documented range.
            if (duration >= 1 && duration <= 3600) url += "&duration=" + Math.round(duration);
        }
        xhr.open("GET", url);
        xhr.setRequestHeader("Lrclib-Client", "Enclosure v1 (https://github.com/Rebo-NS4U/rebos_enclosure)");
        xhr.onreadystatechange = () => {
            if (xhr.readyState !== XMLHttpRequest.DONE || root.request !== xhr || root.trackKey !== key) return;
            root.request = null; timeout.stop();
            if (!searching && (xhr.status === 404 || xhr.status === 400)) {
                root.lookup(key, true); return;
            }
            if (xhr.status === 404) { root.status = "No lyrics found on LRCLIB for this song."; return; }
            if (xhr.status === 429) { root.status = "LRCLIB is busy. Try again shortly."; return; }
            if (xhr.status !== 200) { root.status = "LRCLIB unavailable. Try again shortly."; return; }
            try {
                const response = JSON.parse(xhr.responseText);
                const data = searching ? Lyrics.bestMatch(response, title, artists, album, duration) : response;
                const synced = typeof data?.syncedLyrics === "string" ? data.syncedLyrics.trim() : "";
                const plainText = typeof data?.plainLyrics === "string" ? data.plainLyrics.trim() : "";
                if (!data || (!synced && !plainText && !data.instrumental)) {
                    if (!searching) { root.lookup(key, true); return; }
                    root.status = "No lyrics found on LRCLIB for this song."; return;
                }
                const hit = {text: synced || plainText, instrumental: !!data.instrumental};
                if (Object.keys(root.cache).length >= 40) root.cache = ({});
                root.cache[key] = hit;
                root.apply(hit.text, "LRCLIB", hit.instrumental);
            } catch (error) { root.status = "Could not read LRCLIB lyrics. Try again."; }
        };
        timeout.start(); xhr.send();
    }
    onTrackKeyChanged: debounce.restart()
    onSuppliedChanged: debounce.restart()
    onWantedChanged: { if (wanted) debounce.restart(); else cancel(); }
    Timer { id: debounce; interval: 250; onTriggered: root.refresh() }
    Timer {
        id: timeout; interval: 12000
        onTriggered: { root.cancel(); root.status = "Lyrics request timed out. Try again."; }
    }
    Component.onDestruction: cancel()
}
