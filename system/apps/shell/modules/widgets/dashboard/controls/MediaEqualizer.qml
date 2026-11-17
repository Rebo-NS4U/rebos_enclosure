import QtQuick
import QtQuick.Window
import qs.modules.theme

AudioEqualizerPanel {
    objectName: "media-equalizer"
    compact: true
    property real reservedHeight: Styling.spacing(360)
    availableHeight: Math.max(120, (Screen.height > 0 ? Screen.height : 1000) - reservedHeight - 32)
}
