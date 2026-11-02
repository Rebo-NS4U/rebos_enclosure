//@ pragma UseQApplication
//@ pragma ShellId rebos-fans
import Quickshell
import qs.modules.widgets.config
ShellRoot {
    FanControlWindow { visible: true; onVisibleChanged: if (!visible) Qt.quit() }
}
