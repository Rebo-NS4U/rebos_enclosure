pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
Singleton {
    id: root
    property var wallpaperPalette: ({})
    // Read the shell's wallpaper roles without running any theme exporters.
    property FileView paletteFile: FileView {
        path: Quickshell.env("HOME") + "/.cache/rebos_shell/colors.json"
        watchChanges: true
        preload: true
        onFileChanged: reload()
        onLoaded: {
            try {
                const values = JSON.parse(text());
                const palette = {};
                for (const name in values)
                    if (typeof values[name] === "string" && /^#[0-9a-fA-F]{6}$/.test(values[name]))
                        palette[name] = values[name];
                root.wallpaperPalette = palette;
            } catch (error) {
                console.warn("Keeping the last wallpaper palette:", error);
            }
        }
    }


        property color background: root.wallpaperPalette.background || "#1a1111"
        property color blue: root.wallpaperPalette.blue || "#cebdfe"
        property color blueContainer: root.wallpaperPalette.blueContainer || "#4c3e76"
        property color blueSource: root.wallpaperPalette.blueSource || "#0000ff"
        property color blueValue: root.wallpaperPalette.blueValue || "#0000ff"
        property color cyan: root.wallpaperPalette.cyan || "#84d5c4"
        property color cyanContainer: root.wallpaperPalette.cyanContainer || "#005045"
        property color cyanSource: root.wallpaperPalette.cyanSource || "#00ffff"
        property color cyanValue: root.wallpaperPalette.cyanValue || "#00ffff"
        property color error: root.wallpaperPalette.error || "#ffb4ab"
        property color errorContainer: root.wallpaperPalette.errorContainer || "#93000a"
        property color green: root.wallpaperPalette.green || "#b7d085"
        property color greenContainer: root.wallpaperPalette.greenContainer || "#3a4d10"
        property color greenSource: root.wallpaperPalette.greenSource || "#00ff00"
        property color greenValue: root.wallpaperPalette.greenValue || "#00ff00"
        property color inverseOnSurface: root.wallpaperPalette.inverseOnSurface || "#382e2d"
        property color inversePrimary: root.wallpaperPalette.inversePrimary || "#904a46"
        property color inverseSurface: root.wallpaperPalette.inverseSurface || "#f1dedd"
        property color lightBlue: root.wallpaperPalette.lightBlue || "#cebdfe"
        property color lightCyan: root.wallpaperPalette.lightCyan || "#84d5c4"
        property color lightGreen: root.wallpaperPalette.lightGreen || "#b7d085"
        property color lightMagenta: root.wallpaperPalette.lightMagenta || "#fcb0d5"
        property color lightRed: root.wallpaperPalette.lightRed || "#ffb4ab"
        property color lightYellow: root.wallpaperPalette.lightYellow || "#dec56e"
        property color magenta: root.wallpaperPalette.magenta || "#fcb0d5"
        property color magentaContainer: root.wallpaperPalette.magentaContainer || "#6c3353"
        property color magentaSource: root.wallpaperPalette.magentaSource || "#ff00ff"
        property color magentaValue: root.wallpaperPalette.magentaValue || "#ff00ff"
        property color overBackground: root.wallpaperPalette.overBackground || "#f1dedd"
        property color overBlue: root.wallpaperPalette.overBlue || "#35275e"
        property color overBlueContainer: root.wallpaperPalette.overBlueContainer || "#e8ddff"
        property color overCyan: root.wallpaperPalette.overCyan || "#00382f"
        property color overCyanContainer: root.wallpaperPalette.overCyanContainer || "#9ff2e0"
        property color overError: root.wallpaperPalette.overError || "#690005"
        property color overErrorContainer: root.wallpaperPalette.overErrorContainer || "#ffdad6"
        property color overGreen: root.wallpaperPalette.overGreen || "#253600"
        property color overGreenContainer: root.wallpaperPalette.overGreenContainer || "#d3ec9e"
        property color overMagenta: root.wallpaperPalette.overMagenta || "#521d3c"
        property color overMagentaContainer: root.wallpaperPalette.overMagentaContainer || "#ffd8e8"
        property color overPrimary: root.wallpaperPalette.overPrimary || "#571d1c"
        property color overPrimaryContainer: root.wallpaperPalette.overPrimaryContainer || "#ffdad7"
        property color overPrimaryFixed: root.wallpaperPalette.overPrimaryFixed || "#3b0809"
        property color overPrimaryFixedVariant: root.wallpaperPalette.overPrimaryFixedVariant || "#733331"
        property color overRed: root.wallpaperPalette.overRed || "#561e19"
        property color overRedContainer: root.wallpaperPalette.overRedContainer || "#ffdad6"
        property color overSecondary: root.wallpaperPalette.overSecondary || "#442928"
        property color overSecondaryContainer: root.wallpaperPalette.overSecondaryContainer || "#ffdad7"
        property color overSecondaryFixed: root.wallpaperPalette.overSecondaryFixed || "#2c1514"
        property color overSecondaryFixedVariant: root.wallpaperPalette.overSecondaryFixedVariant || "#5d3f3d"
        property color overSurface: root.wallpaperPalette.overSurface || "#f1dedd"
        property color overSurfaceVariant: root.wallpaperPalette.overSurfaceVariant || "#d8c2c0"
        property color overTertiary: root.wallpaperPalette.overTertiary || "#402d04"
        property color overTertiaryContainer: root.wallpaperPalette.overTertiaryContainer || "#ffdea7"
        property color overTertiaryFixed: root.wallpaperPalette.overTertiaryFixed || "#271900"
        property color overTertiaryFixedVariant: root.wallpaperPalette.overTertiaryFixedVariant || "#594319"
        property color overWhite: root.wallpaperPalette.overWhite || "#00363d"
        property color overWhiteContainer: root.wallpaperPalette.overWhiteContainer || "#9eeffd"
        property color overYellow: root.wallpaperPalette.overYellow || "#3b2f00"
        property color overYellowContainer: root.wallpaperPalette.overYellowContainer || "#fce186"
        property color outline: root.wallpaperPalette.outline || "#a08c8b"
        property color outlineVariant: root.wallpaperPalette.outlineVariant || "#534342"
        property color primary: root.wallpaperPalette.primary || "#ffb3ae"
        property color primaryContainer: root.wallpaperPalette.primaryContainer || "#733331"
        property color primaryFixed: root.wallpaperPalette.primaryFixed || "#ffdad7"
        property color primaryFixedDim: root.wallpaperPalette.primaryFixedDim || "#ffb3ae"
        property color red: root.wallpaperPalette.red || "#ffb4ab"
        property color redContainer: root.wallpaperPalette.redContainer || "#73332e"
        property color redSource: root.wallpaperPalette.redSource || "#ff0000"
        property color redValue: root.wallpaperPalette.redValue || "#ff0000"
        property color scrim: root.wallpaperPalette.scrim || "#000000"
        property color secondary: root.wallpaperPalette.secondary || "#e7bdb9"
        property color secondaryContainer: root.wallpaperPalette.secondaryContainer || "#5d3f3d"
        property color secondaryFixed: root.wallpaperPalette.secondaryFixed || "#ffdad7"
        property color secondaryFixedDim: root.wallpaperPalette.secondaryFixedDim || "#e7bdb9"
        property color shadow: root.wallpaperPalette.shadow || "#000000"
        property color surface: root.wallpaperPalette.surface || "#1a1111"
        property color surfaceBright: root.wallpaperPalette.surfaceBright || "#423736"
        property color surfaceContainer: root.wallpaperPalette.surfaceContainer || "#271d1d"
        property color surfaceContainerHigh: root.wallpaperPalette.surfaceContainerHigh || "#322827"
        property color surfaceContainerHighest: root.wallpaperPalette.surfaceContainerHighest || "#3d3231"
        property color surfaceContainerLow: root.wallpaperPalette.surfaceContainerLow || "#231919"
        property color surfaceContainerLowest: root.wallpaperPalette.surfaceContainerLowest || "#140c0c"
        property color surfaceDim: root.wallpaperPalette.surfaceDim || "#1a1111"
        property color surfaceTint: root.wallpaperPalette.surfaceTint || "#ffb3ae"
        property color surfaceVariant: root.wallpaperPalette.surfaceVariant || "#534342"
        property color tertiary: root.wallpaperPalette.tertiary || "#e2c28c"
        property color tertiaryContainer: root.wallpaperPalette.tertiaryContainer || "#594319"
        property color tertiaryFixed: root.wallpaperPalette.tertiaryFixed || "#ffdea7"
        property color tertiaryFixedDim: root.wallpaperPalette.tertiaryFixedDim || "#e2c28c"
        property color white: root.wallpaperPalette.white || "#82d3e0"
        property color whiteContainer: root.wallpaperPalette.whiteContainer || "#004f58"
        property color whiteSource: root.wallpaperPalette.whiteSource || "#ffffff"
        property color whiteValue: root.wallpaperPalette.whiteValue || "#ffffff"
        property color yellow: root.wallpaperPalette.yellow || "#dec56e"
        property color yellowContainer: root.wallpaperPalette.yellowContainer || "#554500"
        property color yellowSource: root.wallpaperPalette.yellowSource || "#ffff00"
        property color yellowValue: root.wallpaperPalette.yellowValue || "#ffff00"
        property color sourceColor: root.wallpaperPalette.sourceColor || "#7f2424"
 property color warning: yellow
 property color success: green
}
