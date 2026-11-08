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
    description: "Set transparency, choose where blur appears, then adjust its strength. Changes save and apply automatically."

    // Normalize the former lighter mode into the shared strength scale.
    function normalizeLegacyMode() {
        if (Config.performance.desktopBlur === "light") {
            Config.performance.blurStrength = Math.max(0, Math.round(Config.performance.blurStrength / 2 - 2.78));
            Config.performance.desktopBlur = "medium";
        }
    }
    Component.onCompleted: normalizeLegacyMode()
    function applyPreset(strength) {
        normalizeLegacyMode();
        Config.performance.blurStrength = strength;
        if (Config.performance.desktopBlur === "off") Config.performance.desktopBlur = "medium";
    }
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
            onConfigValueChanged: { const wasReady = ready; ready = false; value = configValue; ready = wasReady; }
            Component.onCompleted: { value = configValue; ready = true; }
            onValueChanged: {
                const percent = Math.round(value * 100);
                if (ready && percent !== Config.theme.shellTransparency) Config.theme.shellTransparency = percent;
            }
        }
        StyledText { text: Math.round(transparencySlider.value * 100) + "%"; Layout.preferredWidth: 50 }
    }
    SettingsButton {
        objectName: "theme-transparency-reset"
        text: "Use theme transparency"
        onClicked: Config.theme.shellTransparency = -1
    }
    StyledText {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        text: "0% is opaque; 100% is transparent. This changes shell menu and panel backgrounds, keeping text solid. App windows and the bar have separate transparency settings."
        color: Colors.overSurfaceVariant
    }
    StyledText { text: "Where blur applies"; font.bold: true }
    SettingsComboBox {
        objectName: "blur-scope"
        Layout.fillWidth: true
        model: [{label: "Everywhere", value: "medium"},
                {label: "Shell panels only", value: "shell"},
                {label: "Off", value: "off"}]
        textRole: "label"
        valueRole: "value"
        currentIndex: Config.performance.desktopBlur === "shell" ? 1 : Config.performance.desktopBlur === "off" ? 2 : 0
        onActivated: {
            root.normalizeLegacyMode();
            Config.performance.desktopBlur = currentValue;
        }
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
            onConfigValueChanged: { const wasReady = ready; ready = false; value = configValue; ready = wasReady; }
            Component.onCompleted: { value = configValue; ready = true; }
            onValueChanged: {
                const percent = Math.round(value * 100);
                if (ready && percent !== Config.performance.blurStrength) Config.performance.blurStrength = percent;
            }
        }
        StyledText { text: Math.round(blurstrengthSlider.value * 100) + "%"; Layout.preferredWidth: 50 }
    }
    StyledText {
        objectName: "blur-preset-status"
        Layout.fillWidth: true
        text: Config.performance.desktopBlur === "off" ? "Blur is off. Your strength is saved for when you turn it back on."
            : Config.performance.blurStrength === 22 ? "Lighter glass · 22%"
            : Config.performance.blurStrength === 50 ? "Full glass · 50%" : "Custom · " + Config.performance.blurStrength + "%"
        color: Colors.overSurfaceVariant
    }
    StyledText {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        text: "Presets set the strength slider. They keep your transparency and blur location; choosing one while blur is off enables blur everywhere. 0% is the softest blur; choose Off to remove it."
        color: Colors.overSurfaceVariant
    }
    GridLayout {
        Layout.fillWidth: true
        columns: root.width < Styling.fontSize(0) * 30 ? 1 : 2
        columnSpacing: 12
        rowSpacing: 12
        Repeater {
            model: [
                {strength: 22, id: "light", label: "Lighter glass", detail: "Set blur strength to 22% for softer glass."},
                {strength: 50, id: "medium", label: "Full glass", detail: "Set blur strength to 50% for fuller glass."}
            ]
            delegate: SettingsSectionCard {
                required property var modelData
                objectName: "desktop-blur-" + modelData.id
                text: modelData.label
                description: modelData.detail
                selected: Config.performance.desktopBlur !== "off" && Config.performance.blurStrength === modelData.strength
                onClicked: root.applyPreset(modelData.strength)
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
