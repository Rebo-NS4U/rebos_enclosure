import QtQuick
import Quickshell
import qs.config
import qs.modules.components
ShellRoot {
    FloatingWindow {
        implicitWidth: 640; implicitHeight: 600
        TypingMenu { id: practice; anchors.fill: parent }
        ContentText { id: content; visible: false; text: "AV fi café 日本語" }
        FontMetrics { id: metrics; font: practice.readingFont }
        Timer {
            interval: 400; running: true; repeat: true
            property int index: 0
            property var families: ["Noto Sans", "JetBrains Mono", "DejaVu Sans"]
            onTriggered: {
                try {
                    if (index > 0) {
                        const glyph = practice.glyphItems[0];
                        if (!glyph || glyph.font.family !== families[index - 1] || glyph.renderType !== Text.QtRendering)
                            throw Error("Rendered typing glyph did not follow system font");
                    }
                    if (index === families.length) { console.log("PASS: system fonts and fractional typing metrics"); Qt.quit(); return; }
                    const family = families[index++];
                    Config.theme.font = family;
                    if (practice.readingFont.family !== family || content.font.family !== family)
                        throw Error("Content did not follow system font: " + family);
                    for (const letter of ["i", "W", "é", "日", "\u0301"])
                        if (Math.abs(practice.characterWidth(letter) - metrics.advanceWidth(letter)) > 0.001)
                            throw Error("Measurement drift: " + family + " " + letter);
                    if (content.renderType !== Text.QtRendering || content.font.hintingPreference !== Font.PreferNoHinting)
                        throw Error("Animated text renderer mismatch");
                    practice.practicing = true;
                    practice.restoring = true;
                    practice.pageSource = "Wide WWW narrow iii café 日本語 ".repeat(1000);
                    practice.fitPage();
                    if (practice.passage.length >= practice.pageSource.length || practice.pageLayout.lines > practice.layoutLineLimit
                        || practice.pageLayout.lineWidths.some(width => width > practice.width))
                        throw Error("Typing layout exceeded viewport bounds");
                } catch (error) { console.error(error); Qt.exit(1); }
            }
        }
    }
}
