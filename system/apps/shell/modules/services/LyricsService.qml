pragma Singleton
import QtQuick
import Quickshell
import "Lyrics.js" as Lyrics

Singleton {
    id: root
    property string pinEdge: ""
    property string pinScreen: ""
    property int viewers: 0
    readonly property bool wanted: viewers > 0 || pinEdge !== ""
    readonly property var player: MprisController.activePlayer
    readonly property string supplied: Lyrics.playerLyrics(player?.metadata)
    readonly property string trackKey: JSON.stringify([player?.dbusName, MprisController.trackTitle,
        MprisController.trackArtists, player?.trackAlbum, Math.round(MprisController.length)])
    property string plain: ""
    property var lines: []
    property string status: "Play a song to see lyrics."
    property string provider: ""
    property var createRequest: () => new XMLHttpRequest()
    property var request: null
    property var cache: ({})
    readonly property int currentLine: Lyrics.activeLine(lines, MprisController.position)

    function pin(edge, screenName) {
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
        lines = Lyrics.parseLrc(text);
        plain = lines.length ? lines.map(line => line.text).join("\n") : text;
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
        status = "Finding lyrics…";
        const xhr = createRequest();
        request = xhr;
        let url = "https://lrclib.net/api/get?track_name=" + encodeURIComponent(MprisController.trackTitle)
            + "&artist_name=" + encodeURIComponent(MprisController.trackArtists);
        if (player.trackAlbum) url += "&album_name=" + encodeURIComponent(player.trackAlbum);
        if (MprisController.length > 0) url += "&duration=" + Math.round(MprisController.length);
        xhr.open("GET", url);
        xhr.setRequestHeader("Lrclib-Client", "Enclosure v1 (https://github.com/Rebo-NS4U/rebos_enclosure)");
        xhr.onreadystatechange = () => {
            if (xhr.readyState !== XMLHttpRequest.DONE || root.request !== xhr || root.trackKey !== key) return;
            root.request = null; timeout.stop();
            if (xhr.status === 404) { root.status = "No lyrics found for this song."; return; }
            if (xhr.status !== 200) { root.status = "Lyrics unavailable. Try again shortly."; return; }
            try {
                const data = JSON.parse(xhr.responseText);
                const hit = {text: data.syncedLyrics || data.plainLyrics || "", instrumental: !!data.instrumental};
                if (Object.keys(root.cache).length >= 40) root.cache = ({});
                root.cache[key] = hit;
                root.apply(hit.text, "LRCLIB", hit.instrumental);
            } catch (error) { root.status = "Could not read lyrics. Try again."; }
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
