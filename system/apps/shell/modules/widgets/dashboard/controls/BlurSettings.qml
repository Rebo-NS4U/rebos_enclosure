pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.config
import qs.modules.components
import qs.modules.services
import qs.modules.theme

SettingsGroup {
    id: root
    title: "Transparency and blur"
    description: "Choose where glass blur appears. Less blur can reduce GPU use during video playback. Changes apply immediately."
    StyledText { text: "Shell background transparency"; font.bold: true }
    RowLayout {
        Layout.fillWidth: true
        StyledSlider {
            id: transparencySlider
            objectName: "transparency-slider"
            Layout.fillWidth: true
            Layout.preferredHeight: 28

            stepSize: 0.01
            snapMode: "always"
            smoothDrag: false
            property bool ready: false
            readonly property real configValue: (Config.theme.shellTransparency < 0 ? (Styling.shellStyle === "glass" || Styling.shellStyle === "colorful" ? 22 : 0) : Config.theme.shellTransparency) / 100
            onConfigValueChanged: value = configValue
            Component.onCompleted: { value = configValue; ready = true; }
            onValueChanged: {
                const percent = Math.round(value * 100);
                if (ready && percent !== Config.theme.shellTransparency) Config.theme.shellTransparency = percent;
            }
        }
        StyledText { text: Math.round(transparencySlider.value * 100) + "%"; Layout.preferredWidth: 50 }
    }
    StyledText { text: "Blur strength"; font.bold: true }
    RowLayout {
        Layout.fillWidth: true
        StyledSlider {
            id: blurstrengthSlider
            objectName: "blur-strength-slider"
            Layout.fillWidth: true
            Layout.preferredHeight: 28
            enabled: Config.performance.desktopBlur !== "off"
            stepSize: 0.01
            snapMode: "always"
            smoothDrag: false
            property bool ready: false
            readonly property real configValue: (Config.performance.blurStrength) / 100
            onConfigValueChanged: value = configValue
            Component.onCompleted: { value = configValue; ready = true; }
            onValueChanged: {
                const percent = Math.round(value * 100);
                if (ready && percent !== Config.performance.blurStrength) Config.performance.blurStrength = percent;
            }
        }
        StyledText { text: Math.round(blurstrengthSlider.value * 100) + "%"; Layout.preferredWidth: 50 }
    }
    SettingsButton {
        text: "Use theme transparency"
        onClicked: Config.theme.shellTransparency = -1
    }
    StyledText {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        text: "Transparency affects shell menu and panel backgrounds, keeping text solid. 0% is opaque. Blur strength applies wherever the selected mode enables blur; 0% is the softest blur."
        color: Colors.overSurfaceVariant
    }
    GridLayout {
        Layout.fillWidth: true
        columns: root.width < Styling.fontSize(0) * 30 ? 1 : 2
        columnSpacing: 12
        rowSpacing: 12
        Repeater {
            model: [
                {mode: "light", label: "Lighter glass", detail: "Softer blur across apps and shell panels, with fewer blur passes."},
                {mode: "shell", label: "Shell panels only", detail: "Keep blur on the bar and shell menus. Remove blur from app windows."},
                {mode: "off", label: "Blur off", detail: "Remove blur everywhere for the lowest blur rendering cost. Transparency stays as configured."},
                {mode: "medium", label: "Full glass", detail: "The original medium blur across apps and shell panels."}
            ]
            delegate: SettingsSectionCard {
                required property var modelData
                objectName: "desktop-blur-" + modelData.mode
                text: modelData.label
                description: modelData.detail
                selected: Config.performance.desktopBlur === modelData.mode
                onClicked: Config.performance.desktopBlur = modelData.mode
            }
        }
    }
    StyledText {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        text: DesktopBlur.error || (DesktopBlur.busy ? "Applying blur settings…" : "Your selection is saved automatically.")
        color: DesktopBlur.error ? Colors.error : Colors.overSurfaceVariant
        font.pixelSize: Styling.fontSize(-1)
    }
}
