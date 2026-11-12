import QtQuick
import "Lyrics.js" as Lyrics

QtObject {
    id: root
    property var lines: []
    property real position: 0
    property bool playing: false
    property real rate: 1
    property bool enabled: false
    property string trackKey: ""
    property real anchorPosition: 0
    property real anchorWall: Date.now()
    property bool anchorPlaying: false
    property real anchorRate: 1
    property int activeIndex: -1
    property int followIndex: -1

    function currentTime() {
        return anchorPosition + (anchorPlaying ? (Date.now() - anchorWall) * anchorRate / 1000 : 0);
    }
    function reanchor() {
        anchorPosition = Math.max(0, position);
        anchorWall = Date.now();
        anchorPlaying = playing;
        anchorRate = Math.max(0, rate);
        resync();
    }
    function resync() {
        cue.stop();
        const at = currentTime();
        activeIndex = Lyrics.activeLine(lines, at);
        const next = activeIndex + 1;
        const upcoming = lines[next];
        const gap = next > 0 ? upcoming?.time - lines[next - 1].time : Infinity;
        // Start centering before the cue, but light the row only when it is sung.
        const move = Math.max(0.4, Math.min(1, gap * 0.3));
        const lead = upcoming ? upcoming.time - move * 0.4 : Infinity;
        followIndex = at >= lead ? next : activeIndex;
        if (!enabled || !playing || rate <= 0 || !upcoming) return;
        const event = lead > at ? lead : upcoming.time;
        cue.interval = Math.max(1, Math.min(2147483647, Math.ceil((event - at) * 1000 / rate)));
        cue.start();
    }
    onPositionChanged: {
        // Ignore tiny differences between the player's extrapolation and our clock.
        // Real seeks and corrections reanchor immediately in either direction.
        if (!playing || Math.abs(position - currentTime()) > 0.12) reanchor();
    }
    onPlayingChanged: reanchor()
    onRateChanged: reanchor()
    onTrackKeyChanged: reanchor()
    onEnabledChanged: reanchor()
    onLinesChanged: reanchor()
    Component.onCompleted: reanchor()
    property Timer cue: Timer { onTriggered: root.resync() }
}
