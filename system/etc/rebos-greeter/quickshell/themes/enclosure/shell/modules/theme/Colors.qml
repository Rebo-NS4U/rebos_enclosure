pragma Singleton
import QtQuick
import Quickshell
import qs.config

Singleton {
    readonly property color background: Config.palette.background || "#111111"
    readonly property color surface: Config.palette.surface || "#191919"
    readonly property color overBackground: Config.palette.overBackground || "#eeeeee"
    readonly property color primary: Config.palette.primary || "#b9a1ff"
    readonly property color overPrimary: Config.palette.overPrimary || "#111111"
    readonly property color secondary: Config.palette.secondary || "#bab0cf"
    readonly property color overSecondary: Config.palette.overSecondary || "#111111"
    readonly property color tertiary: Config.palette.tertiary || "#cfb0c0"
    readonly property color overTertiary: Config.palette.overTertiary || "#111111"
    readonly property color error: Config.palette.error || "#ff8888"
    readonly property color overError: Config.palette.overError || "#111111"
}
