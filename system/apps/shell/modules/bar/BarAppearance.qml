pragma Singleton
import QtQuick
import Quickshell
import qs.config
import qs.modules.theme
import "../../config/defaults/bar.js" as BarDefaults

Singleton {
    id: root
    readonly property color foregroundColor: Colors.overBackground
    // Foreground roles are for content on the bar, never on a primary fill.
    readonly property color mutedColor: Colors.overSurfaceVariant
    readonly property color activeColor: Colors.primary

    function controlColor(enabled: bool): color {
        // Main color for active controls; accent for muted or disabled controls.
        return enabled ? Colors.primary : Colors.secondary;
    }
    function batteryStatusColor(percent: real, charging: bool): color {
        if (charging) return activeColor;
        if (percent <= 20) return Colors.error;
        return foregroundColor;
    }

    readonly property bool instrument: Styling.shellStyle === "instrument"
    readonly property bool themedCorners: instrument || Styling.shellStyle === "frosted"
    readonly property bool framed: bordered
    readonly property int borderWidth: bordered ? 2 : 0
    readonly property color activeWorkspaceOutline: bordered ? Colors.primary : foregroundColor
    // Keep saved glass/classic values compatible with Bordered/Plain.
    readonly property bool bordered: (Config.bar?.islandAppearance ?? BarDefaults.data.islandAppearance) === "glass"
    readonly property var themeSurface: Styling.getStyledRectConfig("bg")
    readonly property color highlightColor: Colors.primary
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
        return bordered ? Qt.alpha(highlightColor, 0.5) : "transparent";
    }
    function clockTint(hovered: bool): color {
        return "transparent";
    }
    function workspaceTint(active: bool, hovered: bool): color {
        return bordered && (active || hovered) ? Qt.alpha(highlightColor, active ? 0.22 : 0.12) : "transparent";
    }
    function reset(): void {
        Config.bar.islandAppearance = BarDefaults.data.islandAppearance;
    }
}
