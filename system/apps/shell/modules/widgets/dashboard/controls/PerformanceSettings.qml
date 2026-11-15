pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.theme
import qs.modules.components
import qs.config

SettingsGroup {
    title: "Visual effects"
    property string settingsSection: "performance"
    description: "Choose which visual effects to use."
    Layout.fillWidth: true





    // Blur Transition toggle
    SettingsToggleRow {
        Layout.fillWidth: true
        label: "Blur Transition"
        description: "Animated blur when opening panels"
        checked: Config.performance.blurTransition
        onToggled: checked => {
            Config.performance.blurTransition = checked;
        }
    }

    // Window Preview toggle
    SettingsToggleRow {
        Layout.fillWidth: true
        label: "Window Preview"
        description: "Show window thumbnails in overview"
        checked: Config.performance.windowPreview
        onToggled: checked => {
            Config.performance.windowPreview = checked;
        }
    }

    // Wavy Line toggle
    SettingsToggleRow {
        Layout.fillWidth: true
        label: "Wavy Line"
        description: "Animated wavy line effect"
        checked: Config.performance.wavyLine
        onToggled: checked => {
            Config.performance.wavyLine = checked;
        }
    }

    // Rotate Cover Art toggle
    SettingsToggleRow {
        Layout.fillWidth: true
        label: "Disable Cover Art Rotation"
        description: "Stop the vinyl disc from spinning"
        checked: !Config.performance.rotateCoverArt
        onToggled: checked => {
            Config.performance.rotateCoverArt = !checked;
        }
    }
}
