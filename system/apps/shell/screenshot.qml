//@ pragma UseQApplication
//@ pragma ShellId enclosure_screenshot
import QtQuick
import Quickshell
import qs.modules.screenshot
ShellRoot {
    ScreenshotController {
        // Release graphics resources when capture/editing finishes.
        exitOnClose: true
    }
}
