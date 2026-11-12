pragma Singleton
import QtQuick
import Quickshell
import qs.config
import qs.modules.theme
import "../../config/defaults/bar.js" as BarDefaults

Singleton {
    id: root
    readonly property color foregroundColor: Colors.overBackground
    readonly property bool instrument: Styling.shellStyle === "instrument"
    readonly property bool framed: polished || instrument
    readonly property color activeWorkspaceOutline: instrument ? Colors.primary : foregroundColor
    readonly property bool polished: (Config.bar?.islandAppearance ?? BarDefaults.data.islandAppearance) === "glass"
    readonly property var themeSurface: Styling.getStyledRectConfig("bg")
    readonly property color highlightColor: Config.resolveColor(Styling.getStyledRectConfig("focus").gradient[0][0])
    readonly property color surfaceColor: Config.resolveColor(themeSurface.gradient[0][0])
    readonly property real opacity: themeSurface.opacity
    // Accent intensity comes from the theme's own highlight/background contrast.
    readonly property real accent: Math.min(1, 4 * Math.max(Math.abs(highlightColor.r - surfaceColor.r),
        Math.abs(highlightColor.g - surfaceColor.g), Math.abs(highlightColor.b - surfaceColor.b)))

    function panelOpacity(expanded: bool): real {
        return expanded ? Styling.getStyledRectConfig("popup").opacity : opacity;
    }
    function panelTint(expanded: bool): color {
        // The background surface already supplies the active theme color.
        return "transparent";
    }
    function panelBorder(expanded: bool): color {
        return Config.resolveColor(Styling.getStyledRectConfig(expanded ? "popup" : "bg").border[0]);
    }
    function clockTint(hovered: bool): color {
        if (instrument)
            return Config.resolveColor(Styling.getStyledRectConfig(hovered ? "focus" : "pane").gradient[0][0]);
        return polished ? Qt.alpha(highlightColor, hovered ? 0.95 : 0.65) : "transparent";
    }
    function reset(): void {
        Config.bar.islandAppearance = BarDefaults.data.islandAppearance;
    }
}
