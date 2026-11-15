pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.config
import "ShellStyles.js" as ShellStyles
Singleton {
    id: root
    readonly property var curatedPalette: ShellStyles.themePalette(Config.theme.shellStyle)
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


        property color background: root.curatedPalette && root.curatedPalette.background !== undefined ? root.curatedPalette.background : (Config.oledMode ? "#000000" : root.wallpaperPalette.background || "#1a1111")
        property color blue: root.curatedPalette && root.curatedPalette.blue !== undefined ? root.curatedPalette.blue : (root.wallpaperPalette.blue || "#cebdfe")
        property color blueContainer: root.curatedPalette && root.curatedPalette.blueContainer !== undefined ? root.curatedPalette.blueContainer : (root.wallpaperPalette.blueContainer || "#4c3e76")
        property color blueSource: root.curatedPalette && root.curatedPalette.blueSource !== undefined ? root.curatedPalette.blueSource : (root.wallpaperPalette.blueSource || "#0000ff")
        property color blueValue: root.curatedPalette && root.curatedPalette.blueValue !== undefined ? root.curatedPalette.blueValue : (root.wallpaperPalette.blueValue || "#0000ff")
        property color cyan: root.curatedPalette && root.curatedPalette.cyan !== undefined ? root.curatedPalette.cyan : (root.wallpaperPalette.cyan || "#84d5c4")
        property color cyanContainer: root.curatedPalette && root.curatedPalette.cyanContainer !== undefined ? root.curatedPalette.cyanContainer : (root.wallpaperPalette.cyanContainer || "#005045")
        property color cyanSource: root.curatedPalette && root.curatedPalette.cyanSource !== undefined ? root.curatedPalette.cyanSource : (root.wallpaperPalette.cyanSource || "#00ffff")
        property color cyanValue: root.curatedPalette && root.curatedPalette.cyanValue !== undefined ? root.curatedPalette.cyanValue : (root.wallpaperPalette.cyanValue || "#00ffff")
        property color error: root.curatedPalette && root.curatedPalette.error !== undefined ? root.curatedPalette.error : (root.wallpaperPalette.error || "#ffb4ab")
        property color errorContainer: root.curatedPalette && root.curatedPalette.errorContainer !== undefined ? root.curatedPalette.errorContainer : (root.wallpaperPalette.errorContainer || "#93000a")
        property color green: root.curatedPalette && root.curatedPalette.green !== undefined ? root.curatedPalette.green : (root.wallpaperPalette.green || "#b7d085")
        property color greenContainer: root.curatedPalette && root.curatedPalette.greenContainer !== undefined ? root.curatedPalette.greenContainer : (root.wallpaperPalette.greenContainer || "#3a4d10")
        property color greenSource: root.curatedPalette && root.curatedPalette.greenSource !== undefined ? root.curatedPalette.greenSource : (root.wallpaperPalette.greenSource || "#00ff00")
        property color greenValue: root.curatedPalette && root.curatedPalette.greenValue !== undefined ? root.curatedPalette.greenValue : (root.wallpaperPalette.greenValue || "#00ff00")
        property color inverseOnSurface: root.curatedPalette && root.curatedPalette.inverseOnSurface !== undefined ? root.curatedPalette.inverseOnSurface : (root.wallpaperPalette.inverseOnSurface || "#382e2d")
        property color inversePrimary: root.curatedPalette && root.curatedPalette.inversePrimary !== undefined ? root.curatedPalette.inversePrimary : (root.wallpaperPalette.inversePrimary || "#904a46")
        property color inverseSurface: root.curatedPalette && root.curatedPalette.inverseSurface !== undefined ? root.curatedPalette.inverseSurface : (root.wallpaperPalette.inverseSurface || "#f1dedd")
        property color lightBlue: root.curatedPalette && root.curatedPalette.lightBlue !== undefined ? root.curatedPalette.lightBlue : (root.wallpaperPalette.lightBlue || "#cebdfe")
        property color lightCyan: root.curatedPalette && root.curatedPalette.lightCyan !== undefined ? root.curatedPalette.lightCyan : (root.wallpaperPalette.lightCyan || "#84d5c4")
        property color lightGreen: root.curatedPalette && root.curatedPalette.lightGreen !== undefined ? root.curatedPalette.lightGreen : (root.wallpaperPalette.lightGreen || "#b7d085")
        property color lightMagenta: root.curatedPalette && root.curatedPalette.lightMagenta !== undefined ? root.curatedPalette.lightMagenta : (root.wallpaperPalette.lightMagenta || "#fcb0d5")
        property color lightRed: root.curatedPalette && root.curatedPalette.lightRed !== undefined ? root.curatedPalette.lightRed : (root.wallpaperPalette.lightRed || "#ffb4ab")
        property color lightYellow: root.curatedPalette && root.curatedPalette.lightYellow !== undefined ? root.curatedPalette.lightYellow : (root.wallpaperPalette.lightYellow || "#dec56e")
        property color magenta: root.curatedPalette && root.curatedPalette.magenta !== undefined ? root.curatedPalette.magenta : (root.wallpaperPalette.magenta || "#fcb0d5")
        property color magentaContainer: root.curatedPalette && root.curatedPalette.magentaContainer !== undefined ? root.curatedPalette.magentaContainer : (root.wallpaperPalette.magentaContainer || "#6c3353")
        property color magentaSource: root.curatedPalette && root.curatedPalette.magentaSource !== undefined ? root.curatedPalette.magentaSource : (root.wallpaperPalette.magentaSource || "#ff00ff")
        property color magentaValue: root.curatedPalette && root.curatedPalette.magentaValue !== undefined ? root.curatedPalette.magentaValue : (root.wallpaperPalette.magentaValue || "#ff00ff")
        property color overBackground: root.curatedPalette && root.curatedPalette.overBackground !== undefined ? root.curatedPalette.overBackground : (root.wallpaperPalette.overBackground || "#f1dedd")
        property color overBlue: root.curatedPalette && root.curatedPalette.overBlue !== undefined ? root.curatedPalette.overBlue : (root.wallpaperPalette.overBlue || "#35275e")
        property color overBlueContainer: root.curatedPalette && root.curatedPalette.overBlueContainer !== undefined ? root.curatedPalette.overBlueContainer : (root.wallpaperPalette.overBlueContainer || "#e8ddff")
        property color overCyan: root.curatedPalette && root.curatedPalette.overCyan !== undefined ? root.curatedPalette.overCyan : (root.wallpaperPalette.overCyan || "#00382f")
        property color overCyanContainer: root.curatedPalette && root.curatedPalette.overCyanContainer !== undefined ? root.curatedPalette.overCyanContainer : (root.wallpaperPalette.overCyanContainer || "#9ff2e0")
        property color overError: root.curatedPalette && root.curatedPalette.overError !== undefined ? root.curatedPalette.overError : (root.wallpaperPalette.overError || "#690005")
        property color overErrorContainer: root.curatedPalette && root.curatedPalette.overErrorContainer !== undefined ? root.curatedPalette.overErrorContainer : (root.wallpaperPalette.overErrorContainer || "#ffdad6")
        property color overGreen: root.curatedPalette && root.curatedPalette.overGreen !== undefined ? root.curatedPalette.overGreen : (root.wallpaperPalette.overGreen || "#253600")
        property color overGreenContainer: root.curatedPalette && root.curatedPalette.overGreenContainer !== undefined ? root.curatedPalette.overGreenContainer : (root.wallpaperPalette.overGreenContainer || "#d3ec9e")
        property color overMagenta: root.curatedPalette && root.curatedPalette.overMagenta !== undefined ? root.curatedPalette.overMagenta : (root.wallpaperPalette.overMagenta || "#521d3c")
        property color overMagentaContainer: root.curatedPalette && root.curatedPalette.overMagentaContainer !== undefined ? root.curatedPalette.overMagentaContainer : (root.wallpaperPalette.overMagentaContainer || "#ffd8e8")
        property color overPrimary: root.curatedPalette && root.curatedPalette.overPrimary !== undefined ? root.curatedPalette.overPrimary : (root.wallpaperPalette.overPrimary || "#571d1c")
        property color overPrimaryContainer: root.curatedPalette && root.curatedPalette.overPrimaryContainer !== undefined ? root.curatedPalette.overPrimaryContainer : (root.wallpaperPalette.overPrimaryContainer || "#ffdad7")
        property color overPrimaryFixed: root.curatedPalette && root.curatedPalette.overPrimaryFixed !== undefined ? root.curatedPalette.overPrimaryFixed : (root.wallpaperPalette.overPrimaryFixed || "#3b0809")
        property color overPrimaryFixedVariant: root.curatedPalette && root.curatedPalette.overPrimaryFixedVariant !== undefined ? root.curatedPalette.overPrimaryFixedVariant : (root.wallpaperPalette.overPrimaryFixedVariant || "#733331")
        property color overRed: root.curatedPalette && root.curatedPalette.overRed !== undefined ? root.curatedPalette.overRed : (root.wallpaperPalette.overRed || "#561e19")
        property color overRedContainer: root.curatedPalette && root.curatedPalette.overRedContainer !== undefined ? root.curatedPalette.overRedContainer : (root.wallpaperPalette.overRedContainer || "#ffdad6")
        property color overSecondary: root.curatedPalette && root.curatedPalette.overSecondary !== undefined ? root.curatedPalette.overSecondary : (root.wallpaperPalette.overSecondary || "#442928")
        property color overSecondaryContainer: root.curatedPalette && root.curatedPalette.overSecondaryContainer !== undefined ? root.curatedPalette.overSecondaryContainer : (root.wallpaperPalette.overSecondaryContainer || "#ffdad7")
        property color overSecondaryFixed: root.curatedPalette && root.curatedPalette.overSecondaryFixed !== undefined ? root.curatedPalette.overSecondaryFixed : (root.wallpaperPalette.overSecondaryFixed || "#2c1514")
        property color overSecondaryFixedVariant: root.curatedPalette && root.curatedPalette.overSecondaryFixedVariant !== undefined ? root.curatedPalette.overSecondaryFixedVariant : (root.wallpaperPalette.overSecondaryFixedVariant || "#5d3f3d")
        property color overSurface: root.curatedPalette && root.curatedPalette.overSurface !== undefined ? root.curatedPalette.overSurface : (root.wallpaperPalette.overSurface || "#f1dedd")
        property color overSurfaceVariant: root.curatedPalette && root.curatedPalette.overSurfaceVariant !== undefined ? root.curatedPalette.overSurfaceVariant : (root.wallpaperPalette.overSurfaceVariant || "#d8c2c0")
        property color overTertiary: root.curatedPalette && root.curatedPalette.overTertiary !== undefined ? root.curatedPalette.overTertiary : (root.wallpaperPalette.overTertiary || "#402d04")
        property color overTertiaryContainer: root.curatedPalette && root.curatedPalette.overTertiaryContainer !== undefined ? root.curatedPalette.overTertiaryContainer : (root.wallpaperPalette.overTertiaryContainer || "#ffdea7")
        property color overTertiaryFixed: root.curatedPalette && root.curatedPalette.overTertiaryFixed !== undefined ? root.curatedPalette.overTertiaryFixed : (root.wallpaperPalette.overTertiaryFixed || "#271900")
        property color overTertiaryFixedVariant: root.curatedPalette && root.curatedPalette.overTertiaryFixedVariant !== undefined ? root.curatedPalette.overTertiaryFixedVariant : (root.wallpaperPalette.overTertiaryFixedVariant || "#594319")
        property color overWhite: root.curatedPalette && root.curatedPalette.overWhite !== undefined ? root.curatedPalette.overWhite : (root.wallpaperPalette.overWhite || "#00363d")
        property color overWhiteContainer: root.curatedPalette && root.curatedPalette.overWhiteContainer !== undefined ? root.curatedPalette.overWhiteContainer : (root.wallpaperPalette.overWhiteContainer || "#9eeffd")
        property color overYellow: root.curatedPalette && root.curatedPalette.overYellow !== undefined ? root.curatedPalette.overYellow : (root.wallpaperPalette.overYellow || "#3b2f00")
        property color overYellowContainer: root.curatedPalette && root.curatedPalette.overYellowContainer !== undefined ? root.curatedPalette.overYellowContainer : (root.wallpaperPalette.overYellowContainer || "#fce186")
        property color outline: root.curatedPalette && root.curatedPalette.outline !== undefined ? root.curatedPalette.outline : (root.wallpaperPalette.outline || "#a08c8b")
        property color outlineVariant: root.curatedPalette && root.curatedPalette.outlineVariant !== undefined ? root.curatedPalette.outlineVariant : (root.wallpaperPalette.outlineVariant || "#534342")
        property color primary: root.curatedPalette && root.curatedPalette.primary !== undefined ? root.curatedPalette.primary : (root.wallpaperPalette.primary || "#ffb3ae")
        property color primaryContainer: root.curatedPalette && root.curatedPalette.primaryContainer !== undefined ? root.curatedPalette.primaryContainer : (root.wallpaperPalette.primaryContainer || "#733331")
        property color primaryFixed: root.curatedPalette && root.curatedPalette.primaryFixed !== undefined ? root.curatedPalette.primaryFixed : (root.wallpaperPalette.primaryFixed || "#ffdad7")
        property color primaryFixedDim: root.curatedPalette && root.curatedPalette.primaryFixedDim !== undefined ? root.curatedPalette.primaryFixedDim : (root.wallpaperPalette.primaryFixedDim || "#ffb3ae")
        property color red: root.curatedPalette && root.curatedPalette.red !== undefined ? root.curatedPalette.red : (root.wallpaperPalette.red || "#ffb4ab")
        property color redContainer: root.curatedPalette && root.curatedPalette.redContainer !== undefined ? root.curatedPalette.redContainer : (root.wallpaperPalette.redContainer || "#73332e")
        property color redSource: root.curatedPalette && root.curatedPalette.redSource !== undefined ? root.curatedPalette.redSource : (root.wallpaperPalette.redSource || "#ff0000")
        property color redValue: root.curatedPalette && root.curatedPalette.redValue !== undefined ? root.curatedPalette.redValue : (root.wallpaperPalette.redValue || "#ff0000")
        property color scrim: root.curatedPalette && root.curatedPalette.scrim !== undefined ? root.curatedPalette.scrim : (root.wallpaperPalette.scrim || "#000000")
        property color secondary: root.curatedPalette && root.curatedPalette.secondary !== undefined ? root.curatedPalette.secondary : (root.wallpaperPalette.secondary || "#e7bdb9")
        property color secondaryContainer: root.curatedPalette && root.curatedPalette.secondaryContainer !== undefined ? root.curatedPalette.secondaryContainer : (root.wallpaperPalette.secondaryContainer || "#5d3f3d")
        property color secondaryFixed: root.curatedPalette && root.curatedPalette.secondaryFixed !== undefined ? root.curatedPalette.secondaryFixed : (root.wallpaperPalette.secondaryFixed || "#ffdad7")
        property color secondaryFixedDim: root.curatedPalette && root.curatedPalette.secondaryFixedDim !== undefined ? root.curatedPalette.secondaryFixedDim : (root.wallpaperPalette.secondaryFixedDim || "#e7bdb9")
        property color shadow: root.curatedPalette && root.curatedPalette.shadow !== undefined ? root.curatedPalette.shadow : (root.wallpaperPalette.shadow || "#000000")
        property color surface: root.curatedPalette && root.curatedPalette.surface !== undefined ? root.curatedPalette.surface : (Config.oledMode ? Qt.rgba(0.06, 0.06, 0.06, 1) : root.wallpaperPalette.surface || "#1a1111")
        property color surfaceBright: root.curatedPalette && root.curatedPalette.surfaceBright !== undefined ? root.curatedPalette.surfaceBright : (root.wallpaperPalette.surfaceBright || "#423736")
        property color surfaceContainer: root.curatedPalette && root.curatedPalette.surfaceContainer !== undefined ? root.curatedPalette.surfaceContainer : (root.wallpaperPalette.surfaceContainer || "#271d1d")
        property color surfaceContainerHigh: root.curatedPalette && root.curatedPalette.surfaceContainerHigh !== undefined ? root.curatedPalette.surfaceContainerHigh : (root.wallpaperPalette.surfaceContainerHigh || "#322827")
        property color surfaceContainerHighest: root.curatedPalette && root.curatedPalette.surfaceContainerHighest !== undefined ? root.curatedPalette.surfaceContainerHighest : (root.wallpaperPalette.surfaceContainerHighest || "#3d3231")
        property color surfaceContainerLow: root.curatedPalette && root.curatedPalette.surfaceContainerLow !== undefined ? root.curatedPalette.surfaceContainerLow : (root.wallpaperPalette.surfaceContainerLow || "#231919")
        property color surfaceContainerLowest: root.curatedPalette && root.curatedPalette.surfaceContainerLowest !== undefined ? root.curatedPalette.surfaceContainerLowest : (Config.oledMode ? "#000000" : root.wallpaperPalette.surfaceContainerLowest || "#140c0c")
        property color surfaceDim: root.curatedPalette && root.curatedPalette.surfaceDim !== undefined ? root.curatedPalette.surfaceDim : (Config.oledMode ? "#000000" : root.wallpaperPalette.surfaceDim || "#1a1111")
        property color surfaceTint: root.curatedPalette && root.curatedPalette.surfaceTint !== undefined ? root.curatedPalette.surfaceTint : (root.wallpaperPalette.surfaceTint || "#ffb3ae")
        property color surfaceVariant: root.curatedPalette && root.curatedPalette.surfaceVariant !== undefined ? root.curatedPalette.surfaceVariant : (root.wallpaperPalette.surfaceVariant || "#534342")
        property color tertiary: root.curatedPalette && root.curatedPalette.tertiary !== undefined ? root.curatedPalette.tertiary : (root.wallpaperPalette.tertiary || "#e2c28c")
        property color tertiaryContainer: root.curatedPalette && root.curatedPalette.tertiaryContainer !== undefined ? root.curatedPalette.tertiaryContainer : (root.wallpaperPalette.tertiaryContainer || "#594319")
        property color tertiaryFixed: root.curatedPalette && root.curatedPalette.tertiaryFixed !== undefined ? root.curatedPalette.tertiaryFixed : (root.wallpaperPalette.tertiaryFixed || "#ffdea7")
        property color tertiaryFixedDim: root.curatedPalette && root.curatedPalette.tertiaryFixedDim !== undefined ? root.curatedPalette.tertiaryFixedDim : (root.wallpaperPalette.tertiaryFixedDim || "#e2c28c")
        property color white: root.curatedPalette && root.curatedPalette.white !== undefined ? root.curatedPalette.white : (root.wallpaperPalette.white || "#82d3e0")
        property color whiteContainer: root.curatedPalette && root.curatedPalette.whiteContainer !== undefined ? root.curatedPalette.whiteContainer : (root.wallpaperPalette.whiteContainer || "#004f58")
        property color whiteSource: root.curatedPalette && root.curatedPalette.whiteSource !== undefined ? root.curatedPalette.whiteSource : (root.wallpaperPalette.whiteSource || "#ffffff")
        property color whiteValue: root.curatedPalette && root.curatedPalette.whiteValue !== undefined ? root.curatedPalette.whiteValue : (root.wallpaperPalette.whiteValue || "#ffffff")
        property color yellow: root.curatedPalette && root.curatedPalette.yellow !== undefined ? root.curatedPalette.yellow : (root.wallpaperPalette.yellow || "#dec56e")
        property color yellowContainer: root.curatedPalette && root.curatedPalette.yellowContainer !== undefined ? root.curatedPalette.yellowContainer : (root.wallpaperPalette.yellowContainer || "#554500")
        property color yellowSource: root.curatedPalette && root.curatedPalette.yellowSource !== undefined ? root.curatedPalette.yellowSource : (root.wallpaperPalette.yellowSource || "#ffff00")
        property color yellowValue: root.curatedPalette && root.curatedPalette.yellowValue !== undefined ? root.curatedPalette.yellowValue : (root.wallpaperPalette.yellowValue || "#ffff00")
        property color sourceColor: root.curatedPalette && root.curatedPalette.sourceColor !== undefined ? root.curatedPalette.sourceColor : (root.wallpaperPalette.sourceColor || "#7f2424")
 property color warning: yellow
 property color success: green
}
