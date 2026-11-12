//@ pragma UseQApplication
//@ pragma ShellId enclosure_screenshot
import QtQuick
import Quickshell
import qs.modules.screenshot
ShellRoot {
    ScreenshotController {
        // Retain theme, QML and graphics resources between captures.
        exitOnClose: false
    }
}
