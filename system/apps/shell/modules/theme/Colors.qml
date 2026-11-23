pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.config
import "ShellStyles.js" as ShellStyles

FileView {
    id: colors
    // QUICKSHELL-GIT: path: Quickshell.cachePath("colors.json")
    path: Quickshell.env("HOME") + "/.cache/rebos_shell/colors.json"
    preload: true
    watchChanges: true
    onFileChanged: {
        reload();
    }
    // Generate only after the new palette has finished loading.
    onLoaded: {
        if (forceExport) {
            generatedPalette = "";
            forceExport = false;
        }
        generationTimer.restart();
    }
    onLoadFailed: generationTimer.restart()

    property Connections oledWatcher: Connections {
        id: oledWatcher
        target: Config
        function onOledModeChanged() {
            generationTimer.restart();
        }
    }

    property Connections themeWatcher: Connections {
        id: themeWatcher
        target: Config.loader
        function onFileChanged() {
            generationTimer.restart();
        }
    }

    property QtCtGenerator qtCtGenerator: QtCtGenerator {
        id: qtCtGenerator
    }

    property GtkGenerator gtkGenerator: GtkGenerator {
        id: gtkGenerator
    }

    property PywalGenerator pywalGenerator: PywalGenerator {
        id: pywalGenerator
    }

    property KittyGenerator kittyGenerator: KittyGenerator {
        id: kittyGenerator
    }

    property NvChadGenerator nvChadGenerator: NvChadGenerator {
        id: nvChadGenerator
    }

    property DiscordGenerator discordGenerator: DiscordGenerator {
        id: discordGenerator
    }

    property string generatedPalette: ""
    property bool forceExport: false
    property bool refreshPending: false
    readonly property bool writersBusy: qtCtGenerator.writer.busy || gtkGenerator.writerProcess.busy
        || pywalGenerator.writerProcess.busy || kittyGenerator.writerProcess.busy
        || nvChadGenerator.writerProcess.busy || discordGenerator.writerProcess.busy
    readonly property bool writersSucceeded: qtCtGenerator.writer.succeeded && gtkGenerator.writerProcess.succeeded
        && pywalGenerator.writerProcess.succeeded && kittyGenerator.writerProcess.succeeded
        && nvChadGenerator.writerProcess.succeeded && discordGenerator.writerProcess.succeeded
    readonly property string appStyle: Config.theme?.shellStyle ?? "glass"
    readonly property real appOpacity: Config.theme?.srBg?.opacity ?? 1
    onAppStyleChanged: generationTimer.restart()
    onAppOpacityChanged: generationTimer.restart()

    function refreshApps(): void {
        forceExport = true;
        reload();
    }

    property IpcHandler themeIpc: IpcHandler {
        target: "theme"
        function status(): string {
            return JSON.stringify({style: colors.appStyle, radius: Styling.radius(0),
                opacity: Styling.getStyledRectConfig("bg").opacity,
                blur: Config.performance.desktopBlur, blurStrength: Config.performance.blurStrength});
        }
        function sync(): void {
            colors.refreshApps();
        }
    }

    property Timer generationTimer: Timer {
        id: generationTimer
        interval: 100
        repeat: false
        onTriggered: {
            if (Config.readOnly) return;
            const raw = {};
            for (const name of colors.availableColorNames) raw[name] = colors[name];
            const palette = ShellStyles.appPalette(colors.appStyle, raw, colors.appOpacity);
            for (const name of colors.availableColorNames) palette[name] = Qt.color(palette[name]);
            palette.availableColorNames = colors.availableColorNames;
            const signature = JSON.stringify([palette, Config.theme.font, Config.theme.fontSize, Config.theme.monoFont, Config.theme.monoFontSize, Config.theme.roundness, Config.theme.animDuration]);
            if (signature === colors.generatedPalette)
                return;
            qtCtGenerator.generate(palette);
            gtkGenerator.generate(palette);
            pywalGenerator.generate(palette);
            kittyGenerator.generate(palette);
            nvChadGenerator.generate(palette);
            discordGenerator.generate(palette);
            colors.generatedPalette = signature;
            colors.refreshPending = true;
            appRefreshTimer.restart();
        }
    }

    // Wait for every serialized exporter, including Spicetify, before notifying apps.
    // A burst of selections shares one refresh using the latest completed files.
    property Timer appRefreshTimer: Timer {
        id: appRefreshTimer
        interval: 500
        repeat: false
        onTriggered: {
            if (colors.writersBusy || generationTimer.running || appRefresher.running) {
                restart();
                return;
            }
            if (!colors.refreshPending)
                return;
            colors.refreshPending = false;
            if (!colors.writersSucceeded) {
                console.warn("App refresh skipped because a color export failed");
                colors.generatedPalette = "";
                return;
            }
            appRefresher.running = true;
        }
    }

    property Process appRefresher: Process {
        id: appRefresher
        command: ["python3", Quickshell.shellPath("scripts/reload_theme_apps.py")]
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0)
                console.warn("App color refresh failed:", exitCode);
            if (colors.refreshPending)
                appRefreshTimer.restart();
        }
        stderr: StdioCollector {
            onStreamFinished: {
                if (text.trim())
                    console.warn("App color refresh:", text.trim());
            }
        }
    }

    adapter: JsonAdapter {
        property color background: "#1a1111"
        property color blue: "#cebdfe"
        property color blueContainer: "#4c3e76"
        property color blueSource: "#0000ff"
        property color blueValue: "#0000ff"
        property color cyan: "#84d5c4"
        property color cyanContainer: "#005045"
        property color cyanSource: "#00ffff"
        property color cyanValue: "#00ffff"
        property color error: "#ffb4ab"
        property color errorContainer: "#93000a"
        property color green: "#b7d085"
        property color greenContainer: "#3a4d10"
        property color greenSource: "#00ff00"
        property color greenValue: "#00ff00"
        property color inverseOnSurface: "#382e2d"
        property color inversePrimary: "#904a46"
        property color inverseSurface: "#f1dedd"
        property color lightBlue: "#cebdfe"
        property color lightCyan: "#84d5c4"
        property color lightGreen: "#b7d085"
        property color lightMagenta: "#fcb0d5"
        property color lightRed: "#ffb4ab"
        property color lightYellow: "#dec56e"
        property color magenta: "#fcb0d5"
        property color magentaContainer: "#6c3353"
        property color magentaSource: "#ff00ff"
        property color magentaValue: "#ff00ff"
        property color overBackground: "#f1dedd"
        property color overBlue: "#35275e"
        property color overBlueContainer: "#e8ddff"
        property color overCyan: "#00382f"
        property color overCyanContainer: "#9ff2e0"
        property color overError: "#690005"
        property color overErrorContainer: "#ffdad6"
        property color overGreen: "#253600"
        property color overGreenContainer: "#d3ec9e"
        property color overMagenta: "#521d3c"
        property color overMagentaContainer: "#ffd8e8"
        property color overPrimary: "#571d1c"
        property color overPrimaryContainer: "#ffdad7"
        property color overPrimaryFixed: "#3b0809"
        property color overPrimaryFixedVariant: "#733331"
        property color overRed: "#561e19"
        property color overRedContainer: "#ffdad6"
        property color overSecondary: "#442928"
        property color overSecondaryContainer: "#ffdad7"
        property color overSecondaryFixed: "#2c1514"
        property color overSecondaryFixedVariant: "#5d3f3d"
        property color overSurface: "#f1dedd"
        property color overSurfaceVariant: "#d8c2c0"
        property color overTertiary: "#402d04"
        property color overTertiaryContainer: "#ffdea7"
        property color overTertiaryFixed: "#271900"
        property color overTertiaryFixedVariant: "#594319"
        property color overWhite: "#00363d"
        property color overWhiteContainer: "#9eeffd"
        property color overYellow: "#3b2f00"
        property color overYellowContainer: "#fce186"
        property color outline: "#a08c8b"
        property color outlineVariant: "#534342"
        property color primary: "#ffb3ae"
        property color primaryContainer: "#733331"
        property color primaryFixed: "#ffdad7"
        property color primaryFixedDim: "#ffb3ae"
        property color red: "#ffb4ab"
        property color redContainer: "#73332e"
        property color redSource: "#ff0000"
        property color redValue: "#ff0000"
        property color scrim: "#000000"
        property color secondary: "#e7bdb9"
        property color secondaryContainer: "#5d3f3d"
        property color secondaryFixed: "#ffdad7"
        property color secondaryFixedDim: "#e7bdb9"
        property color shadow: "#000000"
        property color surface: "#1a1111"
        property color surfaceBright: "#423736"
        property color surfaceContainer: "#271d1d"
        property color surfaceContainerHigh: "#322827"
        property color surfaceContainerHighest: "#3d3231"
        property color surfaceContainerLow: "#231919"
        property color surfaceContainerLowest: "#140c0c"
        property color surfaceDim: "#1a1111"
        property color surfaceTint: "#ffb3ae"
        property color surfaceVariant: "#534342"
        property color tertiary: "#e2c28c"
        property color tertiaryContainer: "#594319"
        property color tertiaryFixed: "#ffdea7"
        property color tertiaryFixedDim: "#e2c28c"
        property color white: "#82d3e0"
        property color whiteContainer: "#004f58"
        property color whiteSource: "#ffffff"
        property color whiteValue: "#ffffff"
        property color yellow: "#dec56e"
        property color yellowContainer: "#554500"
        property color yellowSource: "#ffff00"
        property color yellowValue: "#ffff00"
        property color sourceColor: "#7f2424"
    }

    // OLED only forces pure black for the deepest background. Every other role
    // comes straight from matugen/wallust so chrome tracks the wallpaper hue
    // instead of being crushed into a near-black tint of background.
    readonly property var curatedPalette: ShellStyles.themePalette(Config.theme.shellStyle)
    property color background: curatedPalette && curatedPalette.background !== undefined ? curatedPalette.background : (Config.oledMode ? "#000000" : adapter.background)

    property color surface: curatedPalette && curatedPalette.surface !== undefined ? curatedPalette.surface : (Config.oledMode ? Qt.rgba(0.06, 0.06, 0.06, 1) : adapter.surface)
    property color surfaceBright: curatedPalette && curatedPalette.surfaceBright !== undefined ? curatedPalette.surfaceBright : (adapter.surfaceBright)
    property color surfaceContainer: curatedPalette && curatedPalette.surfaceContainer !== undefined ? curatedPalette.surfaceContainer : (adapter.surfaceContainer)
    property color surfaceContainerHigh: curatedPalette && curatedPalette.surfaceContainerHigh !== undefined ? curatedPalette.surfaceContainerHigh : (adapter.surfaceContainerHigh)
    property color surfaceContainerHighest: curatedPalette && curatedPalette.surfaceContainerHighest !== undefined ? curatedPalette.surfaceContainerHighest : (adapter.surfaceContainerHighest)
    property color surfaceContainerLow: curatedPalette && curatedPalette.surfaceContainerLow !== undefined ? curatedPalette.surfaceContainerLow : (adapter.surfaceContainerLow)
    property color surfaceContainerLowest: curatedPalette && curatedPalette.surfaceContainerLowest !== undefined ? curatedPalette.surfaceContainerLowest : (Config.oledMode ? "#000000" : adapter.surfaceContainerLowest)
    property color surfaceDim: curatedPalette && curatedPalette.surfaceDim !== undefined ? curatedPalette.surfaceDim : (Config.oledMode ? "#000000" : adapter.surfaceDim)
    property color surfaceTint: curatedPalette && curatedPalette.surfaceTint !== undefined ? curatedPalette.surfaceTint : (adapter.surfaceTint)
    property color surfaceVariant: curatedPalette && curatedPalette.surfaceVariant !== undefined ? curatedPalette.surfaceVariant : (adapter.surfaceVariant)

    // Direct color properties from adapter
    property color blue: curatedPalette && curatedPalette.blue !== undefined ? curatedPalette.blue : (adapter.blue)
    property color blueContainer: curatedPalette && curatedPalette.blueContainer !== undefined ? curatedPalette.blueContainer : (adapter.blueContainer)
    property color blueSource: curatedPalette && curatedPalette.blueSource !== undefined ? curatedPalette.blueSource : (adapter.blueSource)
    property color blueValue: curatedPalette && curatedPalette.blueValue !== undefined ? curatedPalette.blueValue : (adapter.blueValue)
    property color cyan: curatedPalette && curatedPalette.cyan !== undefined ? curatedPalette.cyan : (adapter.cyan)
    property color cyanContainer: curatedPalette && curatedPalette.cyanContainer !== undefined ? curatedPalette.cyanContainer : (adapter.cyanContainer)
    property color cyanSource: curatedPalette && curatedPalette.cyanSource !== undefined ? curatedPalette.cyanSource : (adapter.cyanSource)
    property color cyanValue: curatedPalette && curatedPalette.cyanValue !== undefined ? curatedPalette.cyanValue : (adapter.cyanValue)
    property color error: curatedPalette && curatedPalette.error !== undefined ? curatedPalette.error : (adapter.error)
    property color errorContainer: curatedPalette && curatedPalette.errorContainer !== undefined ? curatedPalette.errorContainer : (adapter.errorContainer)
    property color green: curatedPalette && curatedPalette.green !== undefined ? curatedPalette.green : (adapter.green)
    property color greenContainer: curatedPalette && curatedPalette.greenContainer !== undefined ? curatedPalette.greenContainer : (adapter.greenContainer)
    property color greenSource: curatedPalette && curatedPalette.greenSource !== undefined ? curatedPalette.greenSource : (adapter.greenSource)
    property color greenValue: curatedPalette && curatedPalette.greenValue !== undefined ? curatedPalette.greenValue : (adapter.greenValue)
    property color inverseOnSurface: curatedPalette && curatedPalette.inverseOnSurface !== undefined ? curatedPalette.inverseOnSurface : (adapter.inverseOnSurface)
    property color inversePrimary: curatedPalette && curatedPalette.inversePrimary !== undefined ? curatedPalette.inversePrimary : (adapter.inversePrimary)
    property color inverseSurface: curatedPalette && curatedPalette.inverseSurface !== undefined ? curatedPalette.inverseSurface : (adapter.inverseSurface)
    property color lightBlue: curatedPalette && curatedPalette.lightBlue !== undefined ? curatedPalette.lightBlue : (adapter.lightBlue)
    property color lightCyan: curatedPalette && curatedPalette.lightCyan !== undefined ? curatedPalette.lightCyan : (adapter.lightCyan)
    property color lightGreen: curatedPalette && curatedPalette.lightGreen !== undefined ? curatedPalette.lightGreen : (adapter.lightGreen)
    property color lightMagenta: curatedPalette && curatedPalette.lightMagenta !== undefined ? curatedPalette.lightMagenta : (adapter.lightMagenta)
    property color lightRed: curatedPalette && curatedPalette.lightRed !== undefined ? curatedPalette.lightRed : (adapter.lightRed)
    property color lightYellow: curatedPalette && curatedPalette.lightYellow !== undefined ? curatedPalette.lightYellow : (adapter.lightYellow)
    property color magenta: curatedPalette && curatedPalette.magenta !== undefined ? curatedPalette.magenta : (adapter.magenta)
    property color magentaContainer: curatedPalette && curatedPalette.magentaContainer !== undefined ? curatedPalette.magentaContainer : (adapter.magentaContainer)
    property color magentaSource: curatedPalette && curatedPalette.magentaSource !== undefined ? curatedPalette.magentaSource : (adapter.magentaSource)
    property color magentaValue: curatedPalette && curatedPalette.magentaValue !== undefined ? curatedPalette.magentaValue : (adapter.magentaValue)
    property color overBackground: curatedPalette && curatedPalette.overBackground !== undefined ? curatedPalette.overBackground : (adapter.overBackground)
    property color overBlue: curatedPalette && curatedPalette.overBlue !== undefined ? curatedPalette.overBlue : (adapter.overBlue)
    property color overBlueContainer: curatedPalette && curatedPalette.overBlueContainer !== undefined ? curatedPalette.overBlueContainer : (adapter.overBlueContainer)
    property color overCyan: curatedPalette && curatedPalette.overCyan !== undefined ? curatedPalette.overCyan : (adapter.overCyan)
    property color overCyanContainer: curatedPalette && curatedPalette.overCyanContainer !== undefined ? curatedPalette.overCyanContainer : (adapter.overCyanContainer)
    property color overError: curatedPalette && curatedPalette.overError !== undefined ? curatedPalette.overError : (adapter.overError)
    property color overErrorContainer: curatedPalette && curatedPalette.overErrorContainer !== undefined ? curatedPalette.overErrorContainer : (adapter.overErrorContainer)
    property color overGreen: curatedPalette && curatedPalette.overGreen !== undefined ? curatedPalette.overGreen : (adapter.overGreen)
    property color overGreenContainer: curatedPalette && curatedPalette.overGreenContainer !== undefined ? curatedPalette.overGreenContainer : (adapter.overGreenContainer)
    property color overMagenta: curatedPalette && curatedPalette.overMagenta !== undefined ? curatedPalette.overMagenta : (adapter.overMagenta)
    property color overMagentaContainer: curatedPalette && curatedPalette.overMagentaContainer !== undefined ? curatedPalette.overMagentaContainer : (adapter.overMagentaContainer)
    property color overPrimary: curatedPalette && curatedPalette.overPrimary !== undefined ? curatedPalette.overPrimary : (adapter.overPrimary)
    property color overPrimaryContainer: curatedPalette && curatedPalette.overPrimaryContainer !== undefined ? curatedPalette.overPrimaryContainer : (adapter.overPrimaryContainer)
    property color overPrimaryFixed: curatedPalette && curatedPalette.overPrimaryFixed !== undefined ? curatedPalette.overPrimaryFixed : (adapter.overPrimaryFixed)
    property color overPrimaryFixedVariant: curatedPalette && curatedPalette.overPrimaryFixedVariant !== undefined ? curatedPalette.overPrimaryFixedVariant : (adapter.overPrimaryFixedVariant)
    property color overRed: curatedPalette && curatedPalette.overRed !== undefined ? curatedPalette.overRed : (adapter.overRed)
    property color overRedContainer: curatedPalette && curatedPalette.overRedContainer !== undefined ? curatedPalette.overRedContainer : (adapter.overRedContainer)
    property color overSecondary: curatedPalette && curatedPalette.overSecondary !== undefined ? curatedPalette.overSecondary : (adapter.overSecondary)
    property color overSecondaryContainer: curatedPalette && curatedPalette.overSecondaryContainer !== undefined ? curatedPalette.overSecondaryContainer : (adapter.overSecondaryContainer)
    property color overSecondaryFixed: curatedPalette && curatedPalette.overSecondaryFixed !== undefined ? curatedPalette.overSecondaryFixed : (adapter.overSecondaryFixed)
    property color overSecondaryFixedVariant: curatedPalette && curatedPalette.overSecondaryFixedVariant !== undefined ? curatedPalette.overSecondaryFixedVariant : (adapter.overSecondaryFixedVariant)
    property color overSurface: curatedPalette && curatedPalette.overSurface !== undefined ? curatedPalette.overSurface : (adapter.overSurface)
    property color overSurfaceVariant: curatedPalette && curatedPalette.overSurfaceVariant !== undefined ? curatedPalette.overSurfaceVariant : (adapter.overSurfaceVariant)
    property color overTertiary: curatedPalette && curatedPalette.overTertiary !== undefined ? curatedPalette.overTertiary : (adapter.overTertiary)
    property color overTertiaryContainer: curatedPalette && curatedPalette.overTertiaryContainer !== undefined ? curatedPalette.overTertiaryContainer : (adapter.overTertiaryContainer)
    property color overTertiaryFixed: curatedPalette && curatedPalette.overTertiaryFixed !== undefined ? curatedPalette.overTertiaryFixed : (adapter.overTertiaryFixed)
    property color overTertiaryFixedVariant: curatedPalette && curatedPalette.overTertiaryFixedVariant !== undefined ? curatedPalette.overTertiaryFixedVariant : (adapter.overTertiaryFixedVariant)
    property color overWhite: curatedPalette && curatedPalette.overWhite !== undefined ? curatedPalette.overWhite : (adapter.overWhite)
    property color overWhiteContainer: curatedPalette && curatedPalette.overWhiteContainer !== undefined ? curatedPalette.overWhiteContainer : (adapter.overWhiteContainer)
    property color overYellow: curatedPalette && curatedPalette.overYellow !== undefined ? curatedPalette.overYellow : (adapter.overYellow)
    property color overYellowContainer: curatedPalette && curatedPalette.overYellowContainer !== undefined ? curatedPalette.overYellowContainer : (adapter.overYellowContainer)
    property color outline: curatedPalette && curatedPalette.outline !== undefined ? curatedPalette.outline : (adapter.outline)
    property color outlineVariant: curatedPalette && curatedPalette.outlineVariant !== undefined ? curatedPalette.outlineVariant : (adapter.outlineVariant)
    property color primary: curatedPalette && curatedPalette.primary !== undefined ? curatedPalette.primary : (adapter.primary)
    property color primaryContainer: curatedPalette && curatedPalette.primaryContainer !== undefined ? curatedPalette.primaryContainer : (adapter.primaryContainer)
    property color primaryFixed: curatedPalette && curatedPalette.primaryFixed !== undefined ? curatedPalette.primaryFixed : (adapter.primaryFixed)
    property color primaryFixedDim: curatedPalette && curatedPalette.primaryFixedDim !== undefined ? curatedPalette.primaryFixedDim : (adapter.primaryFixedDim)
    property color red: curatedPalette && curatedPalette.red !== undefined ? curatedPalette.red : (adapter.red)
    property color redContainer: curatedPalette && curatedPalette.redContainer !== undefined ? curatedPalette.redContainer : (adapter.redContainer)
    property color redSource: curatedPalette && curatedPalette.redSource !== undefined ? curatedPalette.redSource : (adapter.redSource)
    property color redValue: curatedPalette && curatedPalette.redValue !== undefined ? curatedPalette.redValue : (adapter.redValue)
    property color scrim: curatedPalette && curatedPalette.scrim !== undefined ? curatedPalette.scrim : (adapter.scrim)
    property color secondary: curatedPalette && curatedPalette.secondary !== undefined ? curatedPalette.secondary : (adapter.secondary)
    property color secondaryContainer: curatedPalette && curatedPalette.secondaryContainer !== undefined ? curatedPalette.secondaryContainer : (adapter.secondaryContainer)
    property color secondaryFixed: curatedPalette && curatedPalette.secondaryFixed !== undefined ? curatedPalette.secondaryFixed : (adapter.secondaryFixed)
    property color secondaryFixedDim: curatedPalette && curatedPalette.secondaryFixedDim !== undefined ? curatedPalette.secondaryFixedDim : (adapter.secondaryFixedDim)
    property color shadow: curatedPalette && curatedPalette.shadow !== undefined ? curatedPalette.shadow : (adapter.shadow)
    property color tertiary: curatedPalette && curatedPalette.tertiary !== undefined ? curatedPalette.tertiary : (adapter.tertiary)
    property color tertiaryContainer: curatedPalette && curatedPalette.tertiaryContainer !== undefined ? curatedPalette.tertiaryContainer : (adapter.tertiaryContainer)
    property color tertiaryFixed: curatedPalette && curatedPalette.tertiaryFixed !== undefined ? curatedPalette.tertiaryFixed : (adapter.tertiaryFixed)
    property color tertiaryFixedDim: curatedPalette && curatedPalette.tertiaryFixedDim !== undefined ? curatedPalette.tertiaryFixedDim : (adapter.tertiaryFixedDim)
    property color white: curatedPalette && curatedPalette.white !== undefined ? curatedPalette.white : (adapter.white)
    property color whiteContainer: curatedPalette && curatedPalette.whiteContainer !== undefined ? curatedPalette.whiteContainer : (adapter.whiteContainer)
    property color whiteSource: curatedPalette && curatedPalette.whiteSource !== undefined ? curatedPalette.whiteSource : (adapter.whiteSource)
    property color whiteValue: curatedPalette && curatedPalette.whiteValue !== undefined ? curatedPalette.whiteValue : (adapter.whiteValue)
    property color yellow: curatedPalette && curatedPalette.yellow !== undefined ? curatedPalette.yellow : (adapter.yellow)
    property color yellowContainer: curatedPalette && curatedPalette.yellowContainer !== undefined ? curatedPalette.yellowContainer : (adapter.yellowContainer)
    property color yellowSource: curatedPalette && curatedPalette.yellowSource !== undefined ? curatedPalette.yellowSource : (adapter.yellowSource)
    property color yellowValue: curatedPalette && curatedPalette.yellowValue !== undefined ? curatedPalette.yellowValue : (adapter.yellowValue)
    property color sourceColor: curatedPalette && curatedPalette.sourceColor !== undefined ? curatedPalette.sourceColor : (adapter.sourceColor)

    property color criticalText: curatedPalette && curatedPalette.criticalText !== undefined ? curatedPalette.criticalText : (adapter.yellow)
    property color criticalRed: curatedPalette && curatedPalette.criticalRed !== undefined ? curatedPalette.criticalRed : (adapter.error)

    // Semantic aliases
    property color warning: curatedPalette && curatedPalette.warning !== undefined ? curatedPalette.warning : (adapter.yellow)
    property color success: curatedPalette && curatedPalette.success !== undefined ? curatedPalette.success : (adapter.green)

    // List of available color names for color pickers (excludes internal/source colors)
    readonly property list<string> availableColorNames: ["background", "surface", "surfaceBright", "surfaceContainer", "surfaceContainerHigh", "surfaceContainerHighest", "surfaceContainerLow", "surfaceContainerLowest", "surfaceDim", "surfaceTint", "surfaceVariant", "primary", "primaryContainer", "primaryFixed", "primaryFixedDim", "secondary", "secondaryContainer", "secondaryFixed", "secondaryFixedDim", "tertiary", "tertiaryContainer", "tertiaryFixed", "tertiaryFixedDim", "error", "errorContainer", "overBackground", "overSurface", "overSurfaceVariant", "overPrimary", "overPrimaryContainer", "overPrimaryFixed", "overPrimaryFixedVariant", "overSecondary", "overSecondaryContainer", "overSecondaryFixed", "overSecondaryFixedVariant", "overTertiary", "overTertiaryContainer", "overTertiaryFixed", "overTertiaryFixedVariant", "overError", "overErrorContainer", "outline", "outlineVariant", "inversePrimary", "inverseSurface", "inverseOnSurface", "shadow", "scrim", "blue", "blueContainer", "overBlue", "overBlueContainer", "lightBlue", "cyan", "cyanContainer", "overCyan", "overCyanContainer", "lightCyan", "green", "greenContainer", "overGreen", "overGreenContainer", "lightGreen", "magenta", "magentaContainer", "overMagenta", "overMagentaContainer", "lightMagenta", "red", "redContainer", "overRed", "overRedContainer", "lightRed", "yellow", "yellowContainer", "overYellow", "overYellowContainer", "lightYellow", "white", "whiteContainer", "overWhite", "overWhiteContainer"]
}
