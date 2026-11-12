//@ pragma UseQApplication
//@ pragma ShellId enclosure_screenshot
import QtQuick
import Quickshell
import qs.modules.screenshot
ShellRoot {
    ScreenshotController {
        exitOnClose: true
        Component.onCompleted: capture(Quickshell.env("ENCLOSURE_SCREENSHOT_MODE") || "area")
    }
}
