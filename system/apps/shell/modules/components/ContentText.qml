import QtQuick

// Animated content follows the system/theme font through StyledText. Distance
// field rendering keeps scaled and translated glyphs sharp between pixels.
StyledText {
    renderType: Text.QtRendering
    font.hintingPreference: Font.PreferNoHinting
}
