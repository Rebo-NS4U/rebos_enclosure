import QtQuick
import QtQuick.Layouts
import qs.modules.components
import qs.modules.services
import qs.modules.theme

SettingsGroup {
    id: root
    property bool compact: false
    property real availableHeight: 1000
    readonly property int bandRows: Math.ceil(10 / bandGrid.columns)
    readonly property real bandHeight: compact ? Math.max(32, Math.min(Styling.spacing(96),
        (availableHeight - presetSelector.implicitHeight - Styling.spacing(60) - 32) / bandRows - Styling.fontSize(-4) * 2 - Styling.spacing(6))) : Styling.spacing(160)
    title: compact ? "" : "Output equalizer"
    description: compact ? "" : "Shape playback sound with ten adjustable bands. Microphone audio stays unchanged."
    Flow {
        visible: !root.compact
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
        visible: !root.compact || AudioEqualizer.error.length > 0
        text: AudioEqualizer.error || (AudioEqualizer.enabled
            ? AudioEqualizer.active ? "Processing playback · " + AudioEqualizer.headroom.toFixed(1) + " dB automatic headroom" : "Connecting equalizer…"
            : "Bypassed · choose a preset or adjust bands, then enable EQ.")
        color: AudioEqualizer.error ? Colors.error : Colors.overBackground
        Accessible.role: Accessible.StaticText
    }
    EqualizerPresetSelector {
        id: presetSelector
        showEqActions: root.compact
        Layout.fillWidth: true
    }
    StyledText {
        Layout.fillWidth: true
        visible: !root.compact
        text: "Preset: " + AudioEqualizer.preset + " · ±12 dB per band"
        wrapMode: Text.Wrap
    }
    GridLayout {
        id: bandGrid
        Layout.fillWidth: true
        readonly property real cellMinimum: Math.max(26, Math.ceil(Styling.fontSize(-4) * 3.2))
        columns: Math.max(1, Math.min(10, Math.floor((root.width - 32 + columnSpacing) / (cellMinimum + columnSpacing))))
        columnSpacing: Styling.spacing(2)
        rowSpacing: Styling.spacing(8)
        Repeater {
            model: AudioEqualizer.frequencies
            ColumnLayout {
                required property string modelData
                required property int index
                Layout.fillWidth: true
                Layout.minimumWidth: bandGrid.cellMinimum
                Layout.preferredWidth: bandGrid.cellMinimum
                spacing: Styling.spacing(2)
                StyledText {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.preferredWidth: bandGrid.cellMinimum
                    horizontalAlignment: Text.AlignHCenter
                    font.pixelSize: Styling.fontSize(-4)
                    text: AudioEqualizer.gains[index].toFixed(1)
                }
                ThemeSlider {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: Math.max(24, Styling.spacing(28))
                    Layout.preferredHeight: root.bandHeight
                    orientation: Qt.Vertical
                    objectName: "audio-eq-band-" + index
                    from: -12
                    to: 12
                    stepSize: 0.5
                    value: AudioEqualizer.gains[index]
                    Accessible.name: modelData + " equalizer gain"
                    Accessible.description: "Adjust from minus twelve to plus twelve decibels"
                    onMoved: AudioEqualizer.setBand(index, value)
                }
                StyledText {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.preferredWidth: bandGrid.cellMinimum
                    horizontalAlignment: Text.AlignHCenter
                    font.pixelSize: Styling.fontSize(-4)
                    text: modelData.replace(" kHz", "k").replace(" Hz", "")
                }
            }
        }
    }
    StyledText {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        visible: !root.compact
        text: "Music presets offer starting points for different genres. Other includes YouTube, podcasts, movies and gaming. Adjust any band to create a custom curve; automatic headroom compensates for boosts."
        font.pixelSize: Styling.fontSize(-1)
    }
}
