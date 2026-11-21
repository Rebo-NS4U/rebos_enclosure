pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.modules.components
import qs.modules.widgets.dashboard.controls

GridLayout {
    id: picker
    required property string language
    signal languageSelected(string language)
    columns: 2

    StyledText { text: "Whisper audio mode" }
    SettingsComboBox {
        Layout.fillWidth: true
        readonly property var modes: ["auto", "en", "es", "fr", "de"]
        model: ["Auto · detect language and translate to English",
                "English · transcribe English audio (faster)",
                "Spanish · translate Spanish audio to English",
                "French · translate French audio to English",
                "German · translate German audio to English"]
        currentIndex: Math.max(0, modes.indexOf(picker.language))
        onActivated: index => picker.languageSelected(modes[index])
        Accessible.name: "Whisper audio mode"
    }
}
