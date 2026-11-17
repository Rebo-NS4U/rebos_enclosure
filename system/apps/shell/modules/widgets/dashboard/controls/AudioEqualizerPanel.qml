import QtQuick
import QtQuick.Layouts
import qs.modules.components
import qs.modules.services
import qs.modules.theme

SettingsGroup {
    id: root
    title: "Output equalizer"
    description: "Shape playback sound with ten adjustable bands. Microphone audio stays unchanged."
    Flow {
        Layout.fillWidth: true
        spacing: Styling.spacing(8)
        ThemeButton {
            objectName: "audio-eq-toggle"
            text: AudioEqualizer.enabled ? "EQ enabled" : "EQ bypassed"
            highlighted: AudioEqualizer.enabled
            enabled: AudioEqualizer.initialized
            onClicked: AudioEqualizer.setEnabled(!AudioEqualizer.enabled)
        }
        ThemeButton { text: "Reset to flat"; onClicked: AudioEqualizer.selectPreset("Flat") }
    }
    StyledText {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: AudioEqualizer.error || (AudioEqualizer.enabled
            ? AudioEqualizer.active ? "Processing playback · " + AudioEqualizer.headroom.toFixed(1) + " dB automatic headroom" : "Connecting equalizer…"
            : "Bypassed · choose a preset or adjust bands, then enable EQ.")
        color: AudioEqualizer.error ? Colors.error : Colors.overBackground
        Accessible.role: Accessible.StaticText
    }
    Flow {
        Layout.fillWidth: true
        spacing: Styling.spacing(8)
        Repeater {
            model: Object.keys(AudioEqualizer.presets)
            ThemeButton {
                required property string modelData
                objectName: "audio-eq-preset-" + modelData
                text: modelData
                checked: AudioEqualizer.preset === modelData
                onClicked: AudioEqualizer.selectPreset(modelData)
            }
        }
    }
    StyledText {
        Layout.fillWidth: true
        text: "Preset: " + AudioEqualizer.preset + " · ±12 dB per band"
        wrapMode: Text.Wrap
    }
    GridLayout {
        Layout.fillWidth: true
        columns: width >= Styling.spacing(560) ? 2 : 1
        columnSpacing: Styling.spacing(20)
        rowSpacing: Styling.spacing(8)
        Repeater {
            model: AudioEqualizer.frequencies
            ColumnLayout {
                required property string modelData
                required property int index
                Layout.fillWidth: true
                spacing: Styling.spacing(2)
                RowLayout {
                    Layout.fillWidth: true
                    StyledText { text: modelData; Layout.fillWidth: true }
                    StyledText {
                        text: (AudioEqualizer.gains[index] > 0 ? "+" : "") + AudioEqualizer.gains[index].toFixed(1) + " dB"
                    }
                }
                ThemeSlider {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Styling.spacing(36)
                    objectName: "audio-eq-band-" + index
                    from: -12
                    to: 12
                    stepSize: 0.5
                    value: AudioEqualizer.gains[index]
                    Accessible.name: modelData + " equalizer gain"
                    Accessible.description: "Adjust from minus twelve to plus twelve decibels"
                    onMoved: AudioEqualizer.setBand(index, value)
                }
            }
        }
    }
    StyledText {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: "Music: gentle balance · Speech: clearer voices · Movies: warmth and dialogue · Gaming: mid/high detail · Bass/Treble: focused boosts. Automatic headroom reduces gain when bands are boosted."
        font.pixelSize: Styling.fontSize(-1)
    }
}
