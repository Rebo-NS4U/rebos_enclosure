pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root
    readonly property string sinkName: "enclosure.equalizer"
    readonly property var frequencies: ["31 Hz", "63 Hz", "125 Hz", "250 Hz", "500 Hz", "1 kHz", "2 kHz", "4 kHz", "8 kHz", "16 kHz"]
    readonly property var presets: ({
        "Flat": [0,0,0,0,0,0,0,0,0,0],
        "Music": [2,2,1,0,-1,0,1,2,1,0],
        "Pop": [2, 2, 1, 0, -1, 0, 1, 2, 2, 1],
        "Rock": [2, 2, 1, -1, -1, 1, 2, 3, 2, 1],
        "Hip-Hop": [4, 4, 3, 1, -1, 0, 1, 1, 1, 0],
        "Electronic": [4, 3, 2, 0, -1, 0, 1, 2, 3, 2],
        "Jazz": [1, 1, 0, 0, 1, 1, 2, 1, 1, 0],
        "Classical": [0, 0, 0, 0, 0, 1, 1, 1, 2, 1],
        "Acoustic": [-1, 0, 1, 1, 1, 2, 2, 1, 0, 0],
        "Lo-fi": [2, 2, 1, 0, 0, -1, -1, -2, -3, -4],
        "YouTube": [-2, -1, 0, 0, 1, 2, 2, 1, 0, -1],
        "Podcasts": [-4, -3, -1, 0, 1, 3, 3, 1, -1, -2],
        "Speech": [-5,-4,-2,0,1,3,3,2,0,-2],
        "Movies": [3,2,1,-1,0,2,2,1,0,-1],
        "Gaming": [-2,-2,-1,0,1,2,3,3,1,-1],
        "Bass": [5,4,3,1,0,0,0,0,0,0],
        "Treble": [0,0,0,0,0,0,1,3,4,3],
        "Music Extreme": [6, 6, 3, 0, -3, 0, 3, 6, 3, 0],
        "Pop Extreme": [6, 6, 3, 0, -3, 0, 3, 6, 6, 3],
        "Rock Extreme": [6, 6, 3, -3, -3, 3, 6, 9, 6, 3],
        "Hip-Hop Extreme": [12, 12, 9, 3, -3, 0, 3, 3, 3, 0],
        "Electronic Extreme": [12, 9, 6, 0, -3, 0, 3, 6, 9, 6],
        "Jazz Extreme": [3, 3, 0, 0, 3, 3, 6, 3, 3, 0],
        "Classical Extreme": [0, 0, 0, 0, 0, 3, 3, 3, 6, 3],
        "Acoustic Extreme": [-3, 0, 3, 3, 3, 6, 6, 3, 0, 0],
        "Lo-fi Extreme": [6, 6, 3, 0, 0, -3, -3, -6, -9, -12],
        "YouTube Extreme": [-6, -3, 0, 0, 3, 6, 6, 3, 0, -3],
        "Podcasts Extreme": [-12, -9, -3, 0, 3, 9, 9, 3, -3, -6],
        "Speech Extreme": [-12, -12, -6, 0, 3, 9, 9, 6, 0, -6],
        "Movies Extreme": [9, 6, 3, -3, 0, 6, 6, 3, 0, -3],
        "Gaming Extreme": [-6, -6, -3, 0, 3, 6, 9, 9, 3, -3],
        "Bass Extreme": [12, 12, 9, 3, 0, 0, 0, 0, 0, 0],
        "Treble Extreme": [0, 0, 0, 0, 0, 0, 3, 9, 12, 9]
    })
    readonly property var presetGroups: ({
        "Music": ["Flat", "Pop", "Rock", "Hip-Hop", "Electronic", "Jazz", "Classical", "Acoustic", "Lo-fi"],
        "Other": ["YouTube", "Podcasts", "Movies", "Gaming"],
        "Extreme": [
            "Music Extreme", "Pop Extreme", "Rock Extreme", "Hip-Hop Extreme",
            "Electronic Extreme", "Jazz Extreme", "Classical Extreme", "Acoustic Extreme",
            "Lo-fi Extreme", "YouTube Extreme", "Podcasts Extreme", "Speech Extreme",
            "Movies Extreme", "Gaming Extreme", "Bass Extreme", "Treble Extreme"
        ]
    })
    readonly property var presetDescriptions: ({
        "Flat":"Uncolored reference", "Pop":"Vocals and sparkle", "Rock":"Guitars and punch",
        "Hip-Hop":"Low-end weight", "Electronic":"Bass and bright detail", "Jazz":"Warmth and presence",
        "Classical":"Air and light detail", "Acoustic":"Strings and voices", "Lo-fi":"Warm, softer highs",
        "YouTube":"Balanced video voices", "Podcasts":"Voice intelligibility", "Movies":"Warmth and dialogue",
        "Gaming":"Mid/high detail",
        "Music":"Balanced music", "Speech":"Voice clarity", "Bass":"Low-end boost", "Treble":"High-end boost"
    })
    property var gains: [0,0,0,0,0,0,0,0,0,0]
    property string preset: "Flat"
    property bool enabled: false
    property bool active: false
    property bool initialized: false
    property real headroom: 0
    property string target: ""
    property string output: ""
    property string error: ""
    property var queued: null
    readonly property bool busy: client.running || debounce.running

    function categoryForPreset(name) {
        for (const category of Object.keys(presetGroups)) {
            if (presetGroups[category].includes(name)) return category;
        }
        return "";
    }
    function settings() { return {action:"configure", enabled:enabled, gains:gains, preset:preset, target:target}; }
    function apply() { queued = settings(); debounce.restart(); }
    function setBand(index, value) {
        const next = gains.slice();
        next[index] = Math.round(Math.max(-12, Math.min(12, value)) * 10) / 10;
        gains = next;
        preset = "Custom";
        apply();
    }
    function selectPreset(name) {
        if (!presets[name]) return;
        gains = presets[name].slice();
        preset = name;
        apply();
    }
    function setEnabled(value) { enabled = value; apply(); }
    function setTarget(name) { target = name; apply(); }
    function launch() {
        if (client.running) return;
        const request = queued || {action:"status"};
        queued = null;
        client.command = ["python3", Qt.resolvedUrl("../../scripts/audio_equalizer.py").toString().replace(/^file:\/\//, ""), JSON.stringify(request)];
        client.running = true;
    }
    Timer { id: debounce; interval:120; onTriggered: root.launch() }
    Timer { interval:2000; running:true; repeat:true; onTriggered: if (!root.busy) root.launch() }
    Process {
        id: client
        stdout: StdioCollector { id: response }
        onExited: code => {
            try {
                const state = JSON.parse(response.text);
                root.error = state.error || "";
                root.active = state.active || false;
                root.headroom = state.headroom || 0;
                root.output = state.output || "";
                if (!root.queued && state.gains) {
                    root.enabled = state.enabled;
                    root.gains = state.gains;
                    root.preset = state.preset;
                    root.target = state.target;
                }
                root.initialized = true;
            } catch (_) { root.error = "Equalizer service is unavailable. Retry after checking the audio service."; }
            if (root.queued) Qt.callLater(() => root.launch());
        }
    }
    IpcHandler {
        target: "audioEqualizer"
        function status(): string {
            return JSON.stringify({initialized:root.initialized, enabled:root.enabled, active:root.active,
                preset:root.preset, gains:root.gains, headroom:root.headroom, output:root.output, error:root.error});
        }
    }
    Component.onCompleted: launch()
}
