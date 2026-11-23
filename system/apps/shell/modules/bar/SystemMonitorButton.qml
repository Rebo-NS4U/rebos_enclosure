import QtQuick
import qs.modules.components
import qs.modules.services
import qs.modules.theme

ToggleButton {
    id: root
    required property Item bar
    buttonIcon: Icons.heartbeat
    iconColor: BarAppearance.foregroundColor
    tooltipText: "System Monitor"
    onToggle: function () { Visibilities.toggleSystemMonitor(root.bar?.screen?.name ?? ""); }
}
