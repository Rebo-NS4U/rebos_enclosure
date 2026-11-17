pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.modules.theme

// Only exported visual settings are available to the login renderer.
Singleton {
    id: root
    property var appearance: ({})
    readonly property var palette: appearance.palette || ({})
    readonly property var metrics: appearance.metrics || ({})
    readonly property var theme: Object.assign({
        shellStyle: metrics.style || "quiet", roundness: metrics.radius === undefined ? 16 : metrics.radius,
        font: metrics.font || "JetBrains Mono", fontSize: metrics.fontSize || 14,
        monoFontSize: metrics.fontSize || 14, ditherStrength: 20, shellTransparency: -1,
        shadowXOffset: 0, shadowYOffset: 0, shadowOpacity: 0, shadowColor: "shadow", shadowBlur: 1
    }, appearance.material || {})
    readonly property var display: appearance.display || ({use12hFormat: true, tintEnabled: false})
    readonly property int roundness: theme.roundness
    readonly property string defaultFont: theme.font
    readonly property int animDuration: theme.animDuration || 0
    function resolveColor(value) {
        if (!value) return "transparent";
        if (typeof value === "string" && value.startsWith("#")) return value;
        return palette[value] || Colors[value] || "transparent";
    }
    FileView {
        path: Quickshell.env("ENCLOSURE_GREETER_APPEARANCE") || "/var/lib/rebos-greeter/theme/quickshell.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            try { root.appearance = JSON.parse(text()); }
            catch (e) { console.warn("Invalid greeter appearance:", e); }
        }
    }
}
